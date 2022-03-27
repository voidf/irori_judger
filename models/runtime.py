from turtle import update
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *

class Runtime(Document):
    """OJ支持的提交语言"""
    key = StringField(primary_key=True) # 与评测机语言id保持一致
    name = StringField() # 全名，提交代码显示的东西

    ace = StringField() # 备用 为Ace.js语言高亮特性准备的id
    pygments = StringField() # 语言在pygments里的id
    
    template = StringField() # 代码起步模板
    
    extension = StringField() # 文件智能提交用扩展名识别，注意唯一性

    