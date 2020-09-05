import datetime
import os
import sys
import time

from flask import Flask, current_app, g
from flask_cors import CORS
from flask_mongoengine import MongoEngine


db = MongoEngine()

def create_app() -> Flask:
    flask_app = Flask(__name__)
    # 加载配置
    from app.config import get_config
    _get_config = get_config()
    flask_app.config.from_object(_get_config)

    # 添加上下文
    ctx = flask_app.app_context()
    ctx.push()
    # 添加跨域
    CORS(flask_app, support_credentials=True)

    # 初始化数据库
    db.init_app(flask_app)

    # 分配路由
    from app.util.GreenPrint import GreenPrint

    from app.api.v1.domain import domain_blueprint
    api_v1 = GreenPrint('api', __name__, url_prefix='/api/v1')

    api_v1.register_blueprint(domain_blueprint)

    flask_app.register_blueprint(api_v1)

    return flask_app
