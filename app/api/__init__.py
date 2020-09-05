from flask import g, request, jsonify
from app.common.result import trueReturn, falseReturn
from functools import wraps
import traceback
import hashlib

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