from fastapi import FastAPI, Request
from loguru import logger
import tracemalloc
import uvicorn
tracemalloc.start()
# from judge.models import Judge, Language, LanguageLimit, Problem, RuntimeVersion, Submission, SubmissionTestCase
# from judge.caching import finished_submission
# from judge.bridge.base_handler import ZlibPacketHandler, proxy_list
# from judge import event_poster as event
import time
import json
import hmac
import config
import zlib
from typing import *
import asyncio
import traceback
from fastapi.middleware.cors import CORSMiddleware
# from models.submission import Submission
from models import *
from judge import *
from models.user import AUTHORITY_LEVEL


@logger.catch
async def handler_wrapper(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    j = JudgeHandler(reader, writer, judge_list)
    try:
        await j.handle()
    except:
        j.on_disconnect()
        raise

def preload() -> FastAPI:
    """TODO: 多worker fork出来前先进行一些通用东西的初始化

    tier2: 后期考虑多worker的时候重写一下，不过应该也不会有需要用多worker那么大并发量
    """
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware('http')
    async def cors_everywhere(request: Request, call_next):
        logger.debug(request.headers)
        # logger.debug(await request.body())
        logger.warning(request.cookies)
        # start_time = time.time()
        response = await call_next(request)
        # process_time = time.time() - start_time
        # response.headers["X-Process-Time"] = str(process_time)
        response.headers["Access-Control-Allow-Origin"] = request.headers.get('origin', '*')
        logger.debug(response.headers)        
        return response

    # @app.middleware('https')
    # async def cors_everywhere(request: Request, call_next):
    #     # logger.debug(request.headers)
    #     # start_time = time.time()
    #     response = await call_next(request)
    #     # process_time = time.time() - start_time
    #     # response.headers["X-Process-Time"] = str(process_time)
    #     response.headers["Access-Control-Allow-Origin"] = request.headers.get('origin', '*')
    #     # logger.debug(response.headers)        
    #     return response


    from routers import v1_router
    app.include_router(v1_router)
    return app



app = preload()


@app.on_event('startup')
async def site_startup():
    pass

import sys
async def cmdloop():

    site_server = uvicorn.Server(config=config.static.site_server_config)

    judger_monitor = await asyncio.start_server(
        handler_wrapper,
        **config.static.judger_monitor_config
    )

    async def run_judge():
        async with judger_monitor:
            addr = judger_monitor.sockets[0].getsockname()
            logger.info(f'judger monitor serving on {addr}')
            await judger_monitor.serve_forever()
        logger.info('judger server closed')

    asyncio.create_task(run_judge())

    asyncio.create_task(site_server.serve())

    from prompt_toolkit import PromptSession

    console = PromptSession()

    if not User.objects(authority_level=AUTHORITY_LEVEL[0][0]):
        _hd = await console.prompt_async('default admin handle:')
        while not _hd:
            _hd = await console.prompt_async('default admin handle:')
        _pw = await console.prompt_async('default admin password:')
        while not _pw:
            _pw = await console.prompt_async('default admin password:')
        _admin = User(pk=_hd, authority_level=AUTHORITY_LEVEL[0][0])
        _admin.pw_set(_pw)
        _admin.save()
        logger.info('default admin saved.')
        del _hd, _pw, _admin


    console.message = 'irori console:#'

    while 1:
        try:
            cmd: str = await console.prompt_async()
        except EOFError:
            logger.info('type [q] to exit.')
            continue
        if cmd[:1] == '!':
            await judge_list.judge(int(cmd[1:]), 'ds3', 'CPP20', 'int main(){return 0;}',None,1)
        elif cmd == 'q':
            await site_server.shutdown()
            judger_monitor.close()
            await judger_monitor.wait_closed()
            return
        else:
            try:
                exec(cmd)
            except:
                traceback.print_exc()

# loop: asyncio.BaseEventLoop = None

if __name__ == "__main__":
    # global loop
    asyncio.run(cmdloop())
    # _config.setup_event_loop()
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(site_server.serve())
    # uvicorn.run(app)
    # asyncio.run(entrance(), debug=True)
