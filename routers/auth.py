from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from jose import jwt

import hashlib
import datetime
from config import secret

from fastapi import status

import asyncio
auth_route = APIRouter(
    prefix="/auth",
    tags=["auth | 登录"],
)


class login_form(BaseModel):
    username: str
    password: str



def generate_login_jwt(user: User, expires: float=86400,):
    return jwt.encode(
        {
            'user': str(user.pk),
            'ts': str((datetime.datetime.now()+ datetime.timedelta(seconds=expires)).timestamp())
        },  # payload, 有效载体
        secret.jwt_key,  # 进行加密签名的密钥
    )


login_invalid = HTTPException(401, 'username or password invalid')
@auth_route.post('/login')
async def login_auth(response: Response, f: OAuth2PasswordRequestForm = Depends(), expires:float=86400):
    """用户登录，令牌写在cookie里"""
    if not (u := User.objects(pk=f.username).first()):
        raise login_invalid
    if not u.pw_chk(f.password):
        raise login_invalid

    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires)
    return {"jwt": token}

class register_form(BaseModel):
    username: str
    password: str

@auth_route.post('/register')
async def register_auth(response: Response, f: OAuth2PasswordRequestForm = Depends()):
    """用户注册，令牌写在cookie里"""
    expires = 86400
    if not f.username or not f.password:
        raise HTTPException(400, 'handle or password cannot be empty')
    if User.objects(pk=f.username):
        raise HTTPException(400, 'user handle already exists')
    u = User(pk=f.username)
    u.pw_set(f.password)
    u.save()
    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires)
    return {"jwt": token}



