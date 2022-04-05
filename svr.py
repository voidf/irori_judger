from loguru import logger
import tracemalloc
tracemalloc.start()
# from judge.models import Judge, Language, LanguageLimit, Problem, RuntimeVersion, Submission, SubmissionTestCase
# from judge.caching import finished_submission
# from judge.bridge.base_handler import ZlibPacketHandler, proxy_list
# from judge import event_poster as event
from operator import itemgetter
import time
import json
import hmac
import logging
import zlib
from typing import *
import asyncio
import traceback

# from models.submission import Submission
from models import *
from network import *


judge_list = JudgeList()


async def cmdloop():
    import aioconsole
    while 1:
        cmd: str = await aioconsole.ainput()
        if cmd[:1] == '!':
            await judge_list.judge(int(cmd[1:]), 'ds3', 'CPP20', 'int main(){return 0;}',None,1)
        else:
            try:
                exec(cmd)
            except:
                traceback.print_exc()

if __name__ == "__main__":
    @logger.catch
    async def handler_wrapper(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        j = JudgeHandler(reader, writer, judge_list)
        try:
            await j.handle()
        except:
            j.on_disconnect()
            raise
    
    async def entrance():

        asyncio.ensure_future(cmdloop())
        svr = await asyncio.start_server(
            handler_wrapper,
            '0.0.0.0',
            19998
        )
        addr = svr.sockets[0].getsockname()
        logger.info(f'Serving on {addr}')
        async with svr:
            await svr.serve_forever()
    asyncio.run(entrance(), debug=True)
