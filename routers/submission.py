from fastapi import status
from fastapi import WebSocket
import json
from utils.jwt import should_login
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from models.submission import Submission
from models.submission import Problem

from utils.broadcast import broadcaster

from pydantic import BaseModel
from config import static
from jose import jwt

import hashlib
import datetime

import asyncio
submission_route = APIRouter(
    prefix="/submission",
    tags=["submission | 代码提交"],
    dependencies=[Depends(should_login)]
)


@submission_route.get('/')
async def get_submission_list(page: int = 1, perpage: int = 20):
    perpage = min(static.perpage_limit, perpage)
    page = max(1, page)
    total = len(Submission.objects())
    tail = page * perpage  # 节约几个乘法

    submission_list = [i.get_base_info()
                       for i in Submission.objects()[tail-perpage:tail]]

    return {
        'data': submission_list,
        'perpage': perpage,
        'total': total,
        'has_more': tail < total
    }


class Submit(BaseModel):
    source: str
    problem_id: str
    lang: str


@submission_route.post('/')
async def create_submission(submit: Submit):

    return 'to be done'


@submission_route.websocket('/{submission_id}')
async def submission_async_detail(websocket: WebSocket, submission_id: str):
    """实时评测状态信息转发"""
    async with broadcaster.subscribe(submission_id) as subscriber:
        async for event in subscriber:
            if event.message == 'E':
                await websocket.close(status.WS_1000_NORMAL_CLOSURE)
                return
            await websocket.send_text(event.message)


# from fapi.WebsocketSession import *
# @auth_route.websocket('/ws')


@submission_route.get('/{submission_id}')
async def get_submission(submission_id: str):
    p: Problem = Problem.objects(pk=submission_id).first()
    if not p:
        raise HTTPException(404, 'no such submission')
    return p.get_all_info()


@submission_route.put('/{submission_id}')
async def modify_submission(submission_id: str):
    return 'to be done'


@submission_route.delete('/{submission_id}')
async def delete_submission(submission_id: str):
    return 'to be done'
