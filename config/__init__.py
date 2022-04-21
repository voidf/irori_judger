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
        reload=True,
        workers=4,
    )

with open('secret.yml', 'r') as f:
    secret = JsonDict(yaml.safe_load(f)) # 包含敏感数据的配置