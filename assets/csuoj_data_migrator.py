"""本文件为离线代码，迁移题目数据用"""
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

src = r'C:\Users\ATRI\Desktop\data'
dst = r'D:\SETU\Problems'

import shutil
import yaml

print(os.listdir(src))
for oldid in os.listdir(src):
    newid = 'csu' + oldid
    path = dst+'/'+newid
    shutil.copytree(src+'/'+oldid, path, dirs_exist_ok=True)

    cases = []

    init = {}

    for i in os.listdir(path):
        if i.endswith('.in'):
            cases.append({
                'in': i,
                'out': i[:-3] + '.out'
            })
        if i == 'spj':
            shutil.copy2('assets/spj.py', path)
            init['custom_judge'] = 'spj.py'
            init['unbuffered'] = True
            init['checker'] = {
                'name':'bridged',
                'args':{'files':['spj.elf']}
            }

    
    init['test_cases']=[{'batched':cases,'points':100}]
    if 'custom_judge' in init:
        os.rename(path+'/spj', path+'/spj.elf')
        
    with open(path+'/init.yml', 'w', encoding='utf-8', newline='\n') as f:
        yaml.dump(init, f)



# import zipfile

# p_data = zipfile.ZipFile(r'C:\Users\ATRI\Desktop\data.zip')

# print(p_data.extractall)
