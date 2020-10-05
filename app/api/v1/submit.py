import datetime
import json
import traceback
import os
import re
import requests
from flask import Blueprint
from flask import current_app as flaskapp
from flask import g, jsonify, request
from mongoengine.queryset.visitor import Q
from mongoengine import StringField,IntField,ListField,ReferenceField,BooleanField,DateTimeField
from mongoengine import Document
from app.api import handle_error, verify_params, master_auth
from app.common.result import falseReturn, trueReturn

from app.util.time import get_beijing_time, get_time_range_by_day, ts2beijing
from app import db
import GLOBAL
import docker

import base64
import hashlib
import random
import string

import tarfile

client = docker.from_env()

def copy_to(src, dst):
    name, dst = dst.split(':')
    container = client.containers.get(name)

    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    tar = tarfile.open(src + '.tar', mode='w')
    try:
        tar.add(srcname)
    finally:
        tar.close()

    data = open(src + '.tar', 'rb').read()
    container.put_archive(os.path.dirname(dst), data)

submit_blueprint = Blueprint('submit', __name__, url_prefix='/submit')
dockerclient = docker.from_env()
def randstr(length):
    return ''.join([random.choice(string.ascii_letters) for i in range(length)])

class Problem(Document):
    problem_id = IntField()
    title = StringField()
    description = StringField(default='')
    pdf = StringField(default='')
    time_limit = IntField()
    memory_limit = IntField()
    inputs = ListField(StringField()) # spj和经典数据应该至少存在一组
    outputs = ListField(StringField())
    sp_inputs = ListField(StringField(),default=[])
    sp_outputs = ListField(StringField(),default=[])
    interactor = ListField(StringField(),default=[]) # 交互题？

    def get_json(self) -> dict:
        return {
            'problem_id': self.problem_id,
            'title': self.title,
            'description': self.description,
            'pdf': self.pdf,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit
        }

class Submit(Document):
    problem = ReferenceField(Problem)
    submit_id = IntField()
    score = IntField()
    verdict = ListField(StringField())
    runtime = ListField(IntField()) # ms
    memory = ListField(IntField()) # KB
    plain = StringField() # 可能要鉴权,别人的代码有著作权的
    share = BooleanField(default=False)
    time = DateTimeField()

    def get_json(self) -> dict:
        if self.share:
            return {
                'problem': self.problem,
                'submit_id': self.submit_id,
                'verdict': self.verdict,
                'score': self.score,
                'runtime': self.runtime,
                'memory': self.memory,
                'plain':self.plain,
                'time':self.time
            }
        else:
            return {
                'problem': self.problem,
                'submit_id': self.submit_id,
                'verdict': self.verdict,
                'score': self.score,
                'runtime': self.runtime,
                'memory': self.memory,
                'time':self.time
            }

class User(Document): #标井号的不能给用户看
    qq = IntField() #

    nickname = StringField(default='')

    solved = ListField(ReferenceField(Problem),default=[])
    tried = ListField(ReferenceField(Problem),default=[])
    
    submits = ListField(ReferenceField(Submit),default=[])

    def get_json(self) -> dict:
        return {
            'qq': self.qq,
            'solved': self.solved,
            'tried': self.tried,
            'submits': self.submits,
            'nickname':self.nickname
        }

    @staticmethod
    def get_or_create(qq):
        _t = User.objects(qq=int(qq))
        if _t:
            return _t.first()
        else:
            return User(
                    qq=int(qq),
                    nickname=hashlib.md5(
                        hashlib.md5(bytes(str(qq),'utf-8')).digest()
                    ).hexdigest()[:8]
                ).save()

def compiler(lang,plain_path,O2flag = False):
    if lang == 'python3':
        return 'python3',plain_path
    elif lang == 'g++':
        if O2flag:
            os.system(f'g++ {plain_path} -static -O2 -o {plain_path}.elf')
        else:
            os.system(f'g++ {plain_path} -static -o {plain_path}.elf')
        return f'{plain_path}.elf'
    elif lang == 'gcc':
        if O2flag:
            os.system(f'gcc {plain_path} -static -O2 -o {plain_path}.elf')
        else:
            os.system(f'gcc {plain_path} -static -o {plain_path}.elf')
        return f'{plain_path}.elf'
    else:
        return ''

def run_in_sandbox( 
                executable:str,
                input_files:list,
                time_limit:list,
                memory_limit:list,
                extargs = '',
                output_files=[i+'.out' for i in input_files],
                error_files = [i+'.err' for i in input_files],
                time_limit_reverse=[0 for i in input_files],
                memory_limit_reverse=[0 for i in input_files],
                large_stack=[1<<18 for i in input_files],
                output_limit=[1<<18 for i in input_files],
                process_limit=[1<<18 for i in input_files],
                result_files = [i+'.res' for i in input_files]
            ):
    container = dockerclient.containers.run('sandbox:sb',detach=True)
    
    os.system('docker run -dit --network none --name sbsb sandbox:sb')
    os.system(f'docker cp {executable} sbsb:/bin/sbin')
    for i in input_files:
        os.system(f'docker cp {i} sbsb:/bin/sbin')
    for p,i in enumerate(input_files):
        os.system(f'docker exec sb.elf {executable} {i} {output_files[p]} {error_files[p]} {time_limit[p]} {time_limit_reverse[p]} {memory_limit[p]} {memory_limit_reverse[p]} {large_stack[p]} {output_limit[p]} {process_limit[p]} {result_files[p]} {extargs}')
        os.system(f'docker cp sbsb:')

@submit_blueprint.before_request
def before_request():
    try:
        if request.method == "POST" and request.get_data():
            g.data = request.get_json(silent=True)
        else:
            g.data = {}
    except:
        traceback.print_exc()
        return falseReturn(None, '数据错误')


@submit_blueprint.route('/do', methods=['POST'])
@handle_error
@verify_params(params=['user', 'file', 'lang', 'problem'])
def do_submit():
    usr = User.objects(qq=g.data['user']).first()
    print(User.objects())
    return trueReturn({'info': [_.get_json() for _ in User.objects()]})

