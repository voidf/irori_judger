import json
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from models.problem import Problem
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from config import static
from jose import jwt

import hashlib
import datetime

import asyncio
problem_route = APIRouter(
    prefix="/problem",
    tags=["problem | 问题详细"],
)


@problem_route.get('/')
async def get_problem_list(page: int=1, perpage:int=20):
    perpage = min(static.perpage_limit, perpage)
    page = max(1, page)
    total = len(Problem.objects())
    tail = page * perpage # 节约几个乘法

    problem_list = [i.get_base_info() for i in Problem.objects(excludes=['desc'])[tail-perpage:tail]]

    return {
        'data': problem_list,
        'perpage': perpage,
        'total': total,
        'has_more': tail < total
    }


@problem_route.get('/{problem_id}')
async def get_problem(problem_id: str):
    p: Problem = Problem.objects(pk=problem_id).first()
    if not p:
        raise HTTPException(404, 'no such problem')
    return p.get_all_info()

@problem_route.post('/')
async def create_problem():
    raise HTTPException(402, '你给钱我就写')

@problem_route.put('/{problem_id}')
async def modify_problem(problem_id: str):
    raise HTTPException(402, '你给钱我就写')

@problem_route.delete('/{problem_id}')
async def delete_problem(problem_id: str):
    raise HTTPException(402, '你给钱我就写')