"""本文件为离线代码，迁移题目用"""
import pickle
from dataclasses import dataclass
import datetime
from io import BytesIO
import os, sys
import shutil
import traceback
from loguru import logger
cur = sys.path[0]
parent = cur[:cur.rfind('\\')]
os.chdir(parent)
sys.path.append(parent)
print(sys.path)
# changed to parent path


from mongoengine import *
from models.oss import FileStorage
from config import secret, static
from models.problem import ProblemType, Problem
import json
# ProblemType(pk='spj', help='special judge').save()
# ProblemType(pk='common', help='classical judge').save()

import zipfile

uploaded = zipfile.ZipFile(r'C:\Users\ATRI\Desktop\upload.zip')

zip_index = {}
for i in uploaded.namelist():
    if i.find('problem_attach') != -1:
        sp = i.split('/')
        if len(sp) == 3 and sp[-1]:
            zip_index.setdefault(sp[1], []).append(sp)
            # zip_index.append(sp)

print(zip_index)

@dataclass
class ProblemMD:
    _id: int
    description: str
    input: str
    output: str
    hint: str
    source: str
    author: str
    def __getitem__(self, item):
        return getattr(self, item)
    def items(self): return self.__dict__.items()

@dataclass
class ProblemRAW:
    _id: int
    title: str
    description: str
    input: str
    output: str
    sample_input: str
    sample_output: str
    spj: str
    hint: str
    source: str
    in_date: str
    time_limit: int
    memory_limit: int
    defunct: str
    accepted: int
    submit: int
    solved: int
    author: str
    attach: str
    def __getitem__(self, item):
        return getattr(self, item)
    def items(self): return self.__dict__.items()

strbuf = []
numbuf = 0
elembuf = []
entbuf = []
state = None

state_map = {}
# 状态机模式
def EB(c):
    global state
    if c == '(': state = state_map['B']
def B(c):
    global state, numbuf
    if 48 <= ord(c) <= 57:
        numbuf = int(c)
        state = state_map['RI']
    elif c == "'":
        state = state_map['RS']
    elif c == 'N':
        elembuf.append('')
def RS(c):
    global state
    if c == "'": state = state_map['RS2']
    elif c == '\\': state = state_map['RS3']
    else: strbuf.append(c)
def RS2(c):
    global state, elembuf
    if c == "'": state = state_map['RS']
    elif c == ')':
        state = state_map['EB']
        elembuf.append(''.join(strbuf))
        strbuf.clear()
        entbuf.append(elembuf)
        elembuf = []
    elif c == ',':
        state = state_map['B']
        elembuf.append(''.join(strbuf))
        strbuf.clear()
def RI(c):
    global state, numbuf, elembuf
    if 48 <= ord(c) <= 57:
        numbuf = numbuf * 10 + int(c)
    elif c == ')':
        state = state_map['EB']
        elembuf.append(numbuf)
        entbuf.append(elembuf)
        elembuf = []
    elif c == ',':
        state = state_map['B']
        elembuf.append(numbuf)
def RS3(c):
    global state
    if c == "'":
        strbuf.append("'")
        state = RS
    # elif c == '\\':
    #     strbuf.append('\\')
    #     state = RS
    else:
        strbuf.append('\\')
        strbuf.append(c)
        state = RS
state_map = {
    'EB': EB,
    'B': B,
    'RS': RS,
    'RS2': RS2,
    'RS3': RS3,
    'RI': RI,
}
state = EB
with open(r'C:\Users\ATRI\Desktop\problems_md_raw.sql', 'r', encoding='utf-8') as f:
    for c in f.read():
        state(c)
    for ent in entbuf:
        assert len(ent) == 7
    j_md = [ProblemMD(*ent) for ent in entbuf]

# with open(r'C:\Users\ATRI\Desktop\problems_md_raw.pickle', 'wb') as f:
    # pickle.dump(j_md, f)
with open(r'C:\Users\ATRI\Desktop\problems_md_raw.pickle', 'rb') as f:
    j_md = pickle.load(f)

entbuf.clear()
state = EB

# with open(r'C:\Users\ATRI\Desktop\problems_raw.sql', 'r', encoding='utf-8') as f:
#     for c in f.read():
#         state(c)
#     for ent in entbuf:
#         if len(ent) != 19:
#             print(ent)
#         assert len(ent) == 19
#     j_info = [ProblemRAW(*ent) for ent in entbuf]

# with open(r'C:\Users\ATRI\Desktop\problems_raw.pickle', 'wb') as f:
#     pickle.dump(j_info, f)
with open(r'C:\Users\ATRI\Desktop\problems_raw.pickle', 'rb') as f:
    j_info = pickle.load(f)

spj = ProblemType.objects(pk='spj').first()
common = ProblemType.objects(pk='common').first()


details = [
    'description',
    'input',
    'output',
    'hint',
    'source',
    'author',
]
details_mp = {
    'description': 1,
    'input': 2,
    'output': 3,
    'sample_input': 4,
    'sample_output': 5,
    'hint': 6,
    'source': 7,
    'author': 8,
}
# print(md_template)
def decoder2(s):
    return s.replace('\\r', '\r').replace('\\n','\n').replace('\\t','\t')

from codecs import encode, decode
import ast

def decoder1(s):
    try:
        # return decoder2(s)
        return ast.literal_eval(f'"""{s}"""') 
    except:
        traceback.print_exc()
        with open('Exception.txt', 'w', encoding='utf-8') as f:
            f.write(s)
        sys.exit(1)
    # return s.encode('utf-8').decode('unicode-escape')

validator = r'C:\Users\ATRI\Desktop\data'
import re
non_ascii = re.compile(r'[^\x00-\x7F]')

def decoder_all(s) -> str:
    # if re.search(non_ascii, s):
        # return decoder2(s)
    # try:
    return decoder1(s)
    # except:
        # return decoder2(s)
    
def fetcher(id, i):
    flg = False
    try:
        with open(f'{validator}\\{id}\\sample.in') as f:
            fin = f.read()
    except Exception as e:
        if not os.path.exists(f'{validator}\\{id}'):
            f = True
            os.mkdir(f'{validator}\\{id}')
            shutil.copytree(
                r'D:\SETU\irori_judger\assets\sampledir',
                f'D:\\SETU\\Problems\\csu{id}'
            )
        logger.error(e)
        s = decoder_all(i['sample_input'])
        print(s)
        cmd = input('(Y/n)>>>')
        if cmd == 'n':
            sys.exit(1)

        with open(f'{validator}\\{id}\\sample.in', 'w', newline='\n') as f:
            f.write(s)
            if not s.endswith('\n'):
                f.write('\n')
        fin = s

    try:
        with open(f'{validator}\\{id}\\sample.out') as f:
            fout = f.read()
    except Exception as e:
        logger.error(e)
        s = decoder_all(i['sample_output'])
        print(s)
        cmd = input('(Y/n)>>>')
        if cmd == 'n':
            sys.exit(1)
        with open(f'{validator}\\{id}\\sample.out', 'w', newline='\n') as f:
            f.write(s)
            if not s.endswith('\n'):
                f.write('\n')
        fout = s
    if flg:
        shutil.copytree(
            f'{validator}\\{id}', 
            f'D:\\SETU\\Problems\\csu{id}',)
    # with open(f'{validator}\\{id}\\sample.out') as f:
        # fout = f.read()
    return fin, fout



d = {i['_id']:i for i in j_md}
for i in j_info:
    pid = i['_id']
    P = Problem(pk=f'csu{pid}')
    if i['spj'] == '0':
        P.types.append(common)
    else:
        P.types.append(spj)

    P.time_limit = i['time_limit']
    P.memory_limit = i['memory_limit'] * 1024
    P.short_circuit = True
    P.partial = False
    # P.desc_type = Problem.DESC_TYPE[0][0]
    # P.desc = md_template
    fin, fout = fetcher(pid, i)
    desc_list = [
        {
            'head': 'sample_input',
            'body': fin,
            'type': 'copy'
        },
        {
            'head': 'sample_output',
            'body': fout,
            'type': 'copy'
        },
    ]

    # P.desc = P.desc.replace('"sample_input"', i['sample_input'])
    # P.desc = P.desc.replace('"sample_output"', i['sample_output'])
    P.title = i['title']

    if i['defunct'] == '1':
        P.is_public = False
    else:
        P.is_public = True
        P.date = datetime.datetime.strptime(i['in_date'], '%Y-%m-%d %H:%M:%S')

    if minfo:=d.get(pid, None):
        for k, v in minfo.items():
            if isinstance(v, str):
                desc_list.append({'head': k, 'body': v, 'type': 'md'})
        d.pop(pid)
    else:
        for k in details:
            desc_list.append({'head': k, 'body': i[k], 'type': 'html'})
        # P.desc = P.desc.replace('"description"', i['description'])
        # P.desc = P.desc.replace('"input"', i['input'])
        # P.desc = P.desc.replace('"output"', i['output'])
        # P.desc = P.desc.replace('"hint"', i['hint'])
        # P.desc = P.desc.replace('"source"', i['source'])
        # P.desc = P.desc.replace('"author"', i['author'])

    if i.attach in zip_index:
        for fnamelist in zip_index[i.attach]:
            flg = False
            for it in desc_list:
                if it['body'].find(f"/upload/{'/'.join(fnamelist)}") != -1:
                    flg = True
            if flg == False:
                continue

            file_descriptor = uploaded.open('/'.join(fnamelist))
            f_orm = FileStorage.upload(fnamelist[-1], file_descriptor)
            f_orm.uploader = '$CSUOJ_Migrator$'
            f_orm.save()
            for it in desc_list:
                it['body'] = it['body'].replace(f"/upload/{'/'.join(fnamelist)}",f"/oss/{f_orm.pk}")


    nlist = []
    for it in desc_list:
        if it['body'].strip():
            nlist.append(it)
            if nlist[-1]['type'] != 'copy':
                nlist[-1]['body'] = decoder_all(nlist[-1]['body'])
    nlist.sort(key=lambda x:details_mp[x['head']])
    P.desc['default'] = nlist
    P.save()
    print(P.pk)
    

# for pid, it in d.items():
#     P = Problem(pk=f'csu{pid}')
#     for k, v in it.items():
#         if isinstance(v, str):
#             P.desc = P.desc.replace(f'"{k}"', v)
#     P.short_circuit = True
#     P.partial = False
#     P.desc_type = Problem.DESC_TYPE[0][0]
    
#     P.save()




# with open('ato.txt', 'w') as f:
    # for k, v in d.items():
        # f.write(k+'\n')
print(len(j_info), len(j_md), len(d))
