from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.mixin.reportable import Reportable

class Comment(Document, Reportable):
    """树形评论"""
    meta = {'allow_inheritance': True}
    user = ReferenceField(User)
    post_time = DateTimeField()
    update_time = DateTimeField()
    text = StringField() # markdown内容
    allow_reply = BooleanField(default=True)
    reply = ListField(ReferenceField(Comment, reverse_delete_rule=PULL)) # 回复
    likes = IntField(default=0) # 赞数
