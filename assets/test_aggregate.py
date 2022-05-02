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
from models import *
from config import secret, static
from models.problem import ProblemType, Problem
import json

# 单记录的话一般用.next拿第一条记录，注意接表后不能投影as的名字，得as.field来取具体的
tmp = Submission.objects.aggregate([
    {'$match':{'_id': 1}},
    {
        '$lookup':{
            'from': Problem._get_collection_name(),
            'localField': 'problem',
            'foreignField': '_id',
            'as': 'problem'
        },
    },
    {
        '$lookup':{
            'from': ContestParticipation._get_collection_name(),
            'localField': 'participation',
            'foreignField': '_id',
            'as': 'participation'
        }
    },
    {
        '$project':{
            'problem.language_limit': True,
            'problem._id': True,
            'problem.short_circuit': True,
            'problem.time_limit': True,
            'problem.memory_limit': True,
            'is_pretested': True,
            'language': True,
            'date': True,
            'user': True,
            'participation.virtual': True,
        }
    },
])
print(tmp)
print(ct:=tmp.next())
print(type(ct)) # dict
# {'_id': 1, 'participation': [], 'is_pretested': False, 'user': 'yaya', 'problem': [{'_id': 'csu2464', 'time_limit': 1.0, 'memory_limit': 524288, 'short_circuit': True}], 'language': 'CPP20', 'date': datetime.datetime(2022, 3, 9, 23, 33, 22, 191000)}

# Submission.objects(problem__id=pid, participation__id=part_id, user__id=uid,
                                        # date__lt=sub_date, status__nin=('CE', 'IE')).count() + 1
pipeline_result=ct
problem = pipeline_result['problem'][0]
pid = problem['_id']
lang_limits = problem.get('language_limit', [])
time = problem['time_limit']
memory = problem['memory_limit']
short_circuit = problem['short_circuit']
lid = pipeline_result['language']
is_pretested = pipeline_result['is_pretested']
sub_date = pipeline_result['date'] # datetime
uid = pipeline_result['user']
participation = pipeline_result['participation']

if participation:
    part_id = participation[0]['_id']
    part_virtual = participation[0]['virtual']
    tmp = Submission.objects.aggregate([
        {
            '$match':{
                '$and':[
                    {'problem': pid},
                    {'participation':part_id},
                    {'user': uid},
                    {'date': {'$lt': sub_date}},
                    {'status': {'$nin': ('CE', 'IE')}}
                ]
            }
        },{'$count': 'attempt_no'}
    ])
else:
    part_id, part_virtual = None, None

# Submission.objects(pk=id).scalar(
#     'problem__is_public', 'participation__contest__pk',
#     'user', 'problem', 'status', 'language__key',
# ).get()

res = Submission.objects.aggregate([
    {'$match': {'_id': 1}},
    {
        '$lookup':{
            'from': ContestParticipation._get_collection_name(),
            'localField': 'participation',
            'foreignField': '_id',
            'as': 'participation'
        }
    },
    {
        '$lookup':{
            'from': Problem._get_collection_name(),
            'localField': 'problem',
            'foreignField': '_id',
            'as': 'problem'
        }
    },
    {
        '$project':{
            'user': True,
            'problem._id': True,
            'problem.is_public': True,
            'status': True,
            'language': True,
            'participation.contest': True
        }
    }
]).next()
print(res)