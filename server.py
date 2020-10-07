from flask import Flask, request, jsonify, g
from flask_mongoengine import MongoEngine
from mongoengine.queryset.visitor import Q
from mongoengine import StringField, IntField, ListField, ReferenceField, BooleanField, DateTimeField
from mongoengine import Document
from functools import wraps
from flask_cors import CORS
import requests
import datetime
import urllib
import os
import json
import random
import base64
import hashlib
import string
import traceback
import re
import GLOBAL
import docker
import tarfile
import asyncio
import io
from flask import current_app as flaskapp

from typing import List, Optional, Union


# """GLOBAL variables"""
app = Flask(__name__)
client = docker.from_env()

class Config():
    HOST = '0.0.0.0'
    PORT = 14569
    DEBUG = True
    MONGODB_SETTINGS = {
        'db': 'irori_judger',
        'host': 'mongodb://localhost:27017/irori_judger',
    }

# """Data Models"""
class Problem(Document):
    problem_id = StringField()
    title = StringField()
    description = StringField(default='')
    pdf = StringField(default='')
    time_limit = IntField()
    memory_limit = IntField()
    inputs = ListField(StringField(), default=[]) # spj和经典数据应该至少存在一组
    sample_inputs = ListField(StringField(), default=[])
    outputs = ListField(StringField(), default=[])
    sample_outputs = ListField(StringField(), default=[])
    sp_inputs = ListField(StringField(), default=[])
    sp_inputs_lang = StringField()
    sp_outputs = ListField(StringField(), default=[])
    sp_outputs_lang = StringField()
    interactor = ListField(StringField(), default=[]) # 交互题？
    interactor_lang = StringField()
    std = StringField() # 标程

    def get_json(self) -> dict:
        return {
            'problem_id': self.problem_id,
            'title': self.title,
            'description': self.description,
            'pdf': self.pdf,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit,
            'sample_inputs': self.sample_inputs,
            'sample_outputs': self.sample_outputs,
        }

class User(Document): #标井号的不能给用户看
    qq = StringField() #

    nickname = StringField(default='')

    solved = ListField(ReferenceField(Problem),default=[])
    tried = ListField(ReferenceField(Problem),default=[])
    
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
        _t = User.objects(qq=str(qq))
        if _t:
            return _t.first()
        else:
            return User(qq=str(qq)).save()

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
    user = ReferenceField(User)

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



# """General utils"""
def copy_to(src, dst):
    print(src, dst)
    name, dst = dst.split(':')
    container = client.containers.get(name)

    # os.chdir(os.path.dirname(src))
    # srcname = os.path.basename(src)
    f_n = f'{src}.tar'
    with open(f_n, 'w') as f: pass
    tar = tarfile.open(f_n, mode='w')
    try:
        tar.add(src)
    finally:
        tar.close()

    data = open(f_n, 'rb').read()
    print(os.path.dirname(dst))
    container.put_archive(os.path.dirname(dst), data)
    os.remove(f_n)

async def rmTmpFile(fi:str):
    await asyncio.sleep(60)
    os.remove(fi)

def randstr(length):
    return ''.join([random.choice(string.ascii_letters) for i in range(length)])

def compiler(lang, plain_path, O2flag=False) -> str:
    """編譯用戶文件，返回值注意需要解包"""
    if lang == 'python3':
        return f'python3 {plain_path}'
    elif lang == 'g++':
        if O2flag:
            os.system(f'g++ -x c++ {plain_path} -static -O2 -o {plain_path}.elf')
        else:
            os.system(f'g++ -x c++ {plain_path} -static -o {plain_path}.elf')
        return f'{plain_path}.elf'
    elif lang == 'gcc':
        if O2flag:
            os.system(f'gcc -x c {plain_path} -static -O2 -o {plain_path}.elf')
        else:
            os.system(f'gcc -x c {plain_path} -static -o {plain_path}.elf')
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
    output_file:str = '/sandbox/' + input_file + '.out'
    result_file = f'/RESULT.res'
    error_file:str = '/sandbox/' + input_file + '.err'
    print(f'sb.elf {executable} {input_file} {output_file} {error_file} {time_limit} {time_limit_reverse} {memory_limit} {memory_limit_reverse} {large_stack} {output_limit} {process_limit} {result_file} {extargs}')
    container.exec_run('chmod 777 -R /sandbox')
    container.exec_run(f'sb.elf {executable} {input_file} {output_file} {error_file} {time_limit} {time_limit_reverse} {memory_limit} {memory_limit_reverse} {large_stack} {output_limit} {process_limit} {result_file} {extargs}')
    return {
        'res':dict(zip(['bits', 'stat'],container.get_archive(result_file))),
        'out':dict(zip(['bits', 'stat'],container.get_archive(output_file))),
        'err':dict(zip(['bits', 'stat'],container.get_archive(error_file))),
    }

def container_init(exe):
    try: client.containers.get('sbsb').remove(force=True)
    except: pass
    container = client.containers.run('sandbox:sb', stdin_open=True, detach=True, name='sbsb', tty=True, network_disabled=True)
    copy_to(exe,"sbsb:/sandbox/")
    return container

def tar_to_bytes(bits) -> bytes:
    """把get_archieve那个生成器的tar的bits弄成正常bytes拿出来"""
    ttar = next(bits)
    tmptarfn = 'tmptar.tar'
    with open(tmptarfn,'wb') as f:
        f.write(ttar)
    y = tarfile.open(tmptarfn)
    y.extractall(path='Tar/')
    na = 'Tar/' + y.getmembers()[0].name
    with open(na,'rb') as tmp:
        ret = tmp.read()
    os.remove(na)
    os.remove(tmptarfn)
    return ret

def judge_mainwork(executable:str,problem:Problem) -> List[bytes]:
    """沙箱運行用戶可執行文件，返回评测状态verdict，结果res，错误err三元组的列表"""
    realexe = executable.split()[0]
    container = container_init(realexe)    
    # os.system('docker run -dit --network none --name sbsb sandbox:sb')

    # os.system(f'docker cp {executable} sbsb:/usr/sbin/')
    for i in problem.inputs:
        copy_to(i, "sbsb:/sandbox/")
        # os.system(f'docker cp {i} sbsb:/usr/sbin/')
    out = []
    for p,i in enumerate(problem.inputs):
        sandboxmono = sandbox_run(
            container,
            executable,
            i
        )
        # os.system(f'docker exec sb.elf {executable} {i} {output_files[p]} {error_files[p]} {time_limit[p]} {time_limit_reverse[p]} {memory_limit[p]} {memory_limit_reverse[p]} {large_stack[p]} {output_limit[p]} {process_limit[p]} {result_files[p]} {extargs}')
        # out[-1]['out']['bits'] = list(out[-1]['out']['bits'])
        # print(out[-1])
        res = tar_to_bytes(sandboxmono['res']['bits']).decode('utf-8')
        print(res)
        err = tar_to_bytes(sandboxmono['err']['bits']).decode('utf-8')
        print(err)

        if "Exited Normally" in res:
            verdict = checker(problem,tar_to_bytes(sandboxmono['out']['bits']),p)
        else:
            mono = res.split('\n')
            verdict = f'[{mono[0]}] {mono[1]}'
        
        print(verdict)
        out.append([
            verdict,
            res,
            err
        ])
    return out

def checker(problem,participant_ans,itr):
    print(participant_ans)
    out = participant_ans.strip().split(b'\r\n')
    print(itr,len(problem.outputs))
    if len(problem.outputs)>itr:
        
        ans = open(problem.outputs[itr],'rb').read().strip().split(b'\r\n')
        print(out)
        print(ans)
        if len(ans) != len(out):
            return '''[Presentation Error] Length of participant's answer and jury's answer are not equal even after strip().'''
        for p,i,j in zip(range(len(ans)),ans,out):
            if i.strip()!=j.strip():
                return f'''[Wrong Answer] Line {p} differs: Expected {i}, Read {j}.'''
        return '''[Accepted]'''
    return '''[No Test Data]'''

def trueReturn(data=None, msg=""):
    return jsonify({
        'status': True,
        'data': data,
        'msg': msg
    })

def falseReturn(data=None, msg=""):
    return jsonify({
        'status': False,
        'data': data,
        'msg': msg
    })

def smart_decorator(decorator):

    def decorator_proxy(func=None, **kwargs):
        if func is not None:
            return decorator(func=func, **kwargs)

        def decorator_proxy(func):
            return decorator(func=func, **kwargs)

        return decorator_proxy

    return decorator_proxy

def handle_error(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return falseReturn(None, traceback.format_exc())
    return decorator

def uploadToChaoXing(fn: Union[bytes, str]) -> str:
    lnk = 'http://notice.chaoxing.com/pc/files/uploadNoticeFile'
    if isinstance(fn,bytes):
        r = requests.post(lnk,files = {'attrFile':fn})
    else:
        with open(fn,'rb') as f:
            r = requests.post(lnk,files = {'attrFile':f})
    j = json.loads(r.text)
    return j['att_file']['att_clouddisk']['downPath']

@smart_decorator
def verify_params(func, params=[]):
    @wraps(func)
    def decorator(*args, **kwargs):
        for param in params:
            if not g.data or not param in g.data:
                return falseReturn(None, "缺少参数:{}".format(param))
        return func(*args, **kwargs)
    return decorator

@smart_decorator
def master_auth(func, params=[]):
    @wraps(func)
    def decorator(*args, **kwargs):
        if not g.data or hashlib.sha256(bytes(hashlib.sha256(bytes(str(g.data['qq']),'utf-8')).hexdigest(),'utf-8')).hexdigest() not in (
            'd5b41bf99e3474f32e9e80491cadb4bf8b589cdda37abbf38f4908b924c76d19',
            '42eea5cbbb360bdd95134eb1c95ef96d7e3412be7ad2e9cbba83d8f453a5764a'
        ):
            return falseReturn(None, "宁的账号没这个权限= =")
        return func(*args, **kwargs)
    return decorator

app.config.from_object(Config)
CORS(app, support_credentials=True)
db = MongoEngine(app)


if not os.path.exists('./lock'):
    print("init db")
    Problem.objects().delete()
    Submit.objects().delete()
    User.objects().delete()
    try: os.mkdir('Interactor')
    except: traceback.print_exc()
    try: os.mkdir('Input')
    except: traceback.print_exc()
    try: os.mkdir('Output')
    except: traceback.print_exc()
    try: os.mkdir('Submit')
    except: traceback.print_exc()
    open('./lock', 'w').close()
    print("success")




@app.before_request
def before_request():
    try:
        raw_query = request.query_string.decode('utf-8')
        try:
            g.data = request.get_json()
        except:
            g.data = {}
        params = raw_query.split("&")
        g.querys = {}
        for param in params:
            elements = param.split("=")
            if len(elements) == 2:
                g.querys[elements[0]] = elements[1]
    except:
        return falseReturn(None, "data error")


file_extension = {
    'g++':'cpp',
    'gcc':'c',
    'python3':'py'
}


@app.route('/submit', methods=['POST'])
@handle_error
@verify_params(params=['user', 'file', 'lang', 'problem'])
def submit():
    usr = User.get_or_create(qq=g.data['user'])
    problem = Problem.objects(problem_id=g.data['problem']).first()
    
    tmpfile = f'Submit/tmp{usr.qq}_{datetime.datetime.now().timestamp()}.{file_extension[g.data["lang"]]}' 

    with open(tmpfile, 'w', encoding='utf-8') as f:
        f.write(g.data['file'])

    exe = compiler(g.data['lang'], tmpfile, g.data.get('O2', False))
    print(exe)
    res = judge_mainwork(
        executable=exe,
        problem=problem
    )
    os.remove(exe)
    verdict = []
    runtime = []
    memory = []

    for i in res:
        verdict.append(re.search('''\[(.*?)\]''',i[0]).group(1))
        t,m = i[1].split('\n')[-3:-1]
        print(t,m)
        runtime.append(t)
        memory.append(m)
    
    print(res)
    s = Submit(
        problem=problem,
        submit_id=len(Submit.objects()),
        score=int(100*verdict.count('Accept')/len(verdict)),
        verdict=verdict,
        runtime=runtime,
        memory=memory,
        plain=g.data['file'],
        share=g.data.get('share',True),
        time=datetime.datetime.now(),
        user=usr
    ).save()
    return trueReturn({
        'full': res,
        'result': s.get_json()
    })

@app.route('/problem/upload', methods=['POST'])
@handle_error
@verify_params(params=['user', 'title', 'description', 'time_limit', 'memory_limit'])
def problem_upload():
    usr = User.get_or_create(qq=g.data['user'])
    g.data['problem_id'] = len(Problem.objects())
    if 'pdf' in g.data: g.data['pdf'] = uploadToChaoXing(g.data['pdf'])
    if 'inputs' in g.data: # bytes
        til = []
        for p, i in enumerate(g.data['inputs']):
            fn = f'Input/P{g.data["problem_id"]}_{p}.in'
            with open(fn) as f:
                f.write(i)
            til.append(fn)
        g.data['inputs'] = til
    if 'outputs' in g.data: # bytes
        til = []
        for p, i in enumerate(g.data['outputs']):
            fn = f'Output/P{g.data["problem_id"]}_{p}.ans'
            with open(fn) as f:
                f.write(i)
            til.append(fn)
        g.data['outputs'] = til
    if 'sp_inputs' in g.data: # bytes
        til = []
        for p, i in enumerate(g.data['outputs']):
            fn = f'Output/P{g.data["problem_id"]}_{p}.ispj'
            with open(fn) as f:
                f.write(i)
            til.append(fn)
        g.data['outputs'] = til      
    if 'sp_outputs' in g.data: # bytes
        til = []
        for p, i in enumerate(g.data['outputs']):
            fn = f'Output/P{g.data["problem_id"]}_{p}.ospj'
            with open(fn) as f:
                f.write(i)
            til.append(fn)
        g.data['outputs'] = til
    if 'interactor' in g.data: # bytes
        til = []
        for p, i in enumerate(g.data['interactor']):
            fn = f'Interactor/P{g.data["problem_id"]}_{p}.inta'
            with open(fn) as f:
                f.write(i)
            til.append(fn)
        g.data['interactor'] = til
    P = Problem(**g.data).save()

    return trueReturn({'problem': P.get_json()})

@app.route('/problem/import', methods=['POST'])
@handle_error
@verify_params(params=['problem_id', 'title', 'description', 'time_limit', 'memory_limit'])
def problem_import(): return trueReturn({'problem': Problem(**g.data).save().get_json()})

@app.route('/problem/info', methods=['POST'])
@handle_error
@verify_params(params=['problem_id'])
def problem_info(): 
    return trueReturn({
        'problem': Problem.objects(problem_id=g.data['problem_id']).first().get_json()
    })


if __name__ == '__main__':
    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'])

