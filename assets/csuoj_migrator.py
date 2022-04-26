"""本文件为离线代码，迁移题目用"""
import pickle
from dataclasses import dataclass
import datetime
from io import BytesIO
import os, sys
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
    elif c == '\\':
        strbuf.append('\\')
        state = RS
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
# with open(r'C:\Users\ATRI\Desktop\problems_md_raw.sql', 'r', encoding='utf-8') as f:
    # for c in f.read():
        # state(c)
    # for ent in entbuf:
        # assert len(ent) == 7
    # j_md = [ProblemMD(*ent) for ent in entbuf]

# with open(r'C:\Users\ATRI\Desktop\problems_md_raw.pickle', 'wb') as f:
    # pickle.dump(j_md, f)
with open(r'C:\Users\ATRI\Desktop\problems_md_raw.pickle', 'rb') as f:
    j_md = pickle.load(f)

entbuf.clear()
state = EB

# with open(r'C:\Users\ATRI\Desktop\problems_raw.sql', 'r', encoding='utf-8') as f:
    # for c in f.read():
        # state(c)
    # for ent in entbuf:
    #     if len(ent) != 19:
    #         print(ent)
    #     assert len(ent) == 19
    # j_info = [ProblemRAW(*ent) for ent in entbuf]

# with open(r'C:\Users\ATRI\Desktop\problems_raw.pickle', 'wb') as f:
    # pickle.dump(j_info, f)
with open(r'C:\Users\ATRI\Desktop\problems_raw.pickle', 'rb') as f:
    j_info = pickle.load(f)

spj = ProblemType.objects(pk='spj').first()
common = ProblemType.objects(pk='common').first()

r"""
p_info = r'C:\Users\ATRI\Desktop\problem.json'
p_md = r'C:\Users\ATRI\Desktop\problem_md.json'

with open(p_info, 'r', encoding='utf-8') as f_info, open(p_md, 'r', encoding='utf-8') as f_md:
    j_info = json.load(f_info)
    j_md = json.load(f_md)
"""

with open('assets/template_desc_csuoj.md', 'r', encoding='utf-8') as f:
    md_template = f.read()



# print(md_template)
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
    P.desc_type = Problem.DESC_TYPE[0][0]
    P.desc = md_template
    P.desc = P.desc.replace('"sample_input"', i['input'])
    P.desc = P.desc.replace('"sample_output"', i['sample_output'])
    P.title = i['title']

    if i['defunct'] == '1':
        P.is_public = False
    else:
        P.is_public = True
        P.date = datetime.datetime.strptime(i['in_date'], '%Y-%m-%d %H:%M:%S')

    if pid in d:
        minfo = d[pid]
        for k, v in minfo.items():
            if isinstance(v, str):
                P.desc = P.desc.replace(f'"{k}"', v)
        d.pop(pid)
    else:
        P.desc = P.desc.replace('"description"', i['description'])
        P.desc = P.desc.replace('"input"', i['input'])
        P.desc = P.desc.replace('"output"', i['output'])
        P.desc = P.desc.replace('"hint"', i['hint'])
        P.desc = P.desc.replace('"source"', i['source'])
        P.desc = P.desc.replace('"author"', i['author'])

    if i.attach in zip_index:
        for fnamelist in zip_index[i.attach]:
            file_descriptor = uploaded.open('/'.join(fnamelist))
            f_orm = FileStorage.upload(fnamelist[-1], file_descriptor)
            f_orm.uploader = '$CSUOJ_Migrator$'
            f_orm.save()
            P.desc = P.desc.replace(f"/upload/{'/'.join(fnamelist)}", 
                # f"{config.static.oss_host}/oss/{f_orm.pk}"
                f"/oss/{f_orm.pk}" # 用nginx反代把路径代到指定服务器
            )

    P.save()
    

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
