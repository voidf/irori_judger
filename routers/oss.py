from io import BytesIO
from fastapi import APIRouter, HTTPException, Response
from models.oss import FileStorage

from pydantic import BaseModel
from jose import jwt
from urllib.parse import quote

import hashlib
import datetime
from config import secret


import asyncio
oss_route = APIRouter(
    prefix="/oss",
    tags=["oss | 文件存储服务（可以外提）"],
)



@oss_route.get('/{fspk}')
async def download_oss(fspk: str):
    fs: FileStorage = FileStorage.trychk(fspk)

    if not fs:
        raise HTTPException(404, 'No such resource')
    else:
        fn = fs.name
        content_disposition_filename = quote(fn)
        if content_disposition_filename != fn:
            content_disposition = "attachment; filename*=utf-8''{}".format(
                content_disposition_filename
            )
        else:
            content_disposition = f'attachment; filename="{fn}"'
        return Response(fs.content.read(), media_type=fs.mime, headers={
            "content-disposition": content_disposition
        })