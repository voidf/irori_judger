import datetime
import traceback
from jose import jwt
from loguru import logger
from fastapi import Request, HTTPException

from config import secret
from utils.ctx import g
from models.user import User

def verify_login_jwt(token):
    try:
        payload = jwt.decode(token, secret.jwt_key)
        if datetime.datetime.now().timestamp() > float(payload['ts']):
            return None, "token expired"
        if not (u := User.objects(pk=payload['user']).first()):
            return None, "user not exists"
        return u, ""
    except:
        logger.critical(traceback.format_exc())
        return None, "unexpected error"


async def should_login(auth: Request):
    """请求预处理，将令牌放入线程作用域g()"""
    try:
        logger.debug(auth.client.host)
        Authorization = auth.cookies.get('Authorization', None)
        if Authorization:
            g().user, g().msg = verify_login_jwt(Authorization)
            if g().user:
                return g().user
        raise HTTPException(401, "this operation requires login")
    except:
        logger.critical(traceback.format_exc())
        raise HTTPException(400, "data error")
