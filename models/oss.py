from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.mixin.chkable import Chkable
from io import BytesIO
import datetime
import magic

class FileStorage(Document, Chkable):
    name = StringField()
    content = FileField()
    mime = StringField()
    expires = DateTimeField()
    date = DateTimeField()
    uploader = StringField() # 上传者用户handle，为了分离此处不做Ref
    def destroy(self):
        self.content.delete()
        self.delete()
    def upload(fn: str, f: BytesIO):
        """上传者，过期时间不在这里处理"""
        typ = magic.from_buffer(f.read(1024), mime=True)
        f.seek(0)
        f_orm = FileStorage(name=fn, date=datetime.datetime.now(), mime=typ)
        f_orm.content.put(f)
        return f_orm.save()
