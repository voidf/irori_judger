"""读取全局设置文件的模块

计划同时支持env文件和yml文件，后者优先
"""

import yaml
from utils.jsondict import JsonDict
import uvicorn

class static: # 可公开的首选项配置
    judger_monitor_config = {
        'host':'0.0.0.0',
        'port':19998
    }
    site_server_config = uvicorn.Config(
        'svr:app',
        '0.0.0.0',
        19999,
        debug=True,
        # ssl_certfile='ssl/A.crt',
        # ssl_keyfile='ssl/A.key',
        # reload=True,
        workers=1, # 在有有效的迁移方案前先保持单进程运行，大概也够用
        # 要不以后整个服务读写分离吧，写api单线程，与judger交互
    )
    perpage_limit = 50 # 分页元素个数最大限制
    source_code_limit = 256 * 1024 # 源码长度限制
    oss_host = 'http://127.0.0.1'
    authenticate_judger = False # 是否开启评测机口令认证

    submission_case_max_feedback = 65536 # 提交返信长度限制
    judge_handler_update_rate_time = 0.5
    judge_handler_update_rate_limit = 5

with open('secret.yml', 'r') as f:
    secret = JsonDict(yaml.safe_load(f)) # 包含敏感数据的配置