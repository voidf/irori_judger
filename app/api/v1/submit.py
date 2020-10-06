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
from typing import List
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
    """編譯用戶文件，返回值注意需要解包"""
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

def sandbox_run(
    container,
    executable:str,
    input_file:str,
    time_limit = 10,
    time_limit_reverse = 0,
    memory_limit = 1<<19, # 512M
    memory_limit_reverse = 0,
    large_stack = 1<<19,
    output_limit = 1<<19<<4, # 8M
    process_limit = 1<<19<<4,
    extargs = ''
):
    output_file:str = input_file + '.out'
    result_file = input_file + '.res'
    error_file:str = input_file + '.err'

    container.exec_run(f'sb.elf {executable} {input_file} {output_file} {error_file} {time_limit} {time_limit_reverse} {memory_limit} {memory_limit_reverse} {large_stack} {output_limit} {process_limit} {result_files} {extargs}')
    return {
        'res':dict(zip(['bits','stat'],container.get_archive(result_file))),
        'out':dict(zip(['bits','stat'],container.get_archive(output_file))),
        'err':dict(zip(['bits','stat'],container.get_archive(error_file))),
    }

def container_init(exe):
    container = dockerclient.containers.run('sandbox:sb',detach=True)
    copy_to(exe,"sbsb:/bin/sbin")
    return container

def judge_mainwork(executable:str,problem:Problem) -> List[bytes]:
    """沙箱運行用戶可執行文件，返回文件二進制"""
    container=container_init(executable)    
    # os.system('docker run -dit --network none --name sbsb sandbox:sb')

    # os.system(f'docker cp {executable} sbsb:/bin/sbin')
    for i in problem.input_files:
        copy_to(i, "sbsb:/bin/sbin")
        # os.system(f'docker cp {i} sbsb:/bin/sbin')
    out = []
    for p,i in enumerate(problem.input_files):
        out.append(sandbox_run(
            container,
            executable,
            i
        ))
        # os.system(f'docker exec sb.elf {executable} {i} {output_files[p]} {error_files[p]} {time_limit[p]} {time_limit_reverse[p]} {memory_limit[p]} {memory_limit_reverse[p]} {large_stack[p]} {output_limit[p]} {process_limit[p]} {result_files[p]} {extargs}')
        
        out[-1]['verdict'] = checker(problem,out[-1]['out'],p)
        print(out[-1])
        # os.system(f'docker cp sbsb:')
    return out

def checker(problem,participant_ans,itr):
    out = participant_ans.strip().split()
    if len(problem.outputs)<itr:
        ans = open(problem.outputs[itr],'rb').read().strip().split()
        if len(ans) != len(out):
            return '''[Presentation Error] Length of participant's answer and jury's answer are not equal even after strip().'''
        for p,i,j in zip(range(len(ans)),ans,out):
            if i.strip()!=j.strip():
                return f'''[Wrong Answer] Line {p} differs: Expected {i}, Read {j}.'''
        return '''[Accepted]'''
    return '''[No Test Data]'''

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
    # print(User.objects())
    problem = Problem.objects(problem_id=g.data['problem'])

    tmpfile = 'tmp' + randstr(6)

    with open(tmpfile,'wb') as f:
        f.write(g.data['file'])


    exe,*ext = compiler(g.data['lang'],tmpfile,g.data.get('O2',False))
    res = judge_mainwork(
        executable = exe,
        problem = problem
    )

    return trueReturn({'result': res})

