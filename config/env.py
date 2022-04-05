"""读取全局设置文件的模块

计划同时支持env文件和yml文件，后者优先
"""

try:
    import os
    db_auth = os.environ["DBAUTH"]
except KeyError:
    from dotenv import load_dotenv
    load_dotenv()
    db_auth = os.environ["DBAUTH"]
