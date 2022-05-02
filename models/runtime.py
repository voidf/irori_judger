from mongoengine.queryset import CASCADE
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.mixin.expandable import Expandable
from models.mixin.chkable import Chkable


class Runtime(Document, Expandable, Chkable):
    """OJ支持的提交语言"""
    key = StringField(primary_key=True) # 与评测机语言id保持一致
    
    name = StringField() # 全名，提交代码显示的东西

    ace = StringField() # 备用 为Ace.js语言高亮特性准备的id
    pygments = StringField() # 语言在pygments里的id
    
    template = StringField() # 代码起步模板
    
    extension = StringField() # 文件智能提交用扩展名识别，注意唯一性

class RuntimeVersion(Document, Expandable, Chkable):
    """评测机上的具体运行时版本，没有则创建一个"""
    language = ReferenceField(Runtime, reverse_delete_rule=CASCADE)
    name = StringField(primary_key=True)
    version = StringField()

    @classmethod
    def runtime_chk(cls, lang: str, version: list):
        for p, i in enumerate(version):
            version[p] = i[0] + '/' + '.'.join(str(x) for x in i[1])
        
        formatted_version = ', '.join(version)
        r = cls.chk(f'{lang} ({formatted_version})')
        r.language = Runtime.chk(lang)
        r.version = formatted_version
        return r.save()
    
    def get_readable(self):
        return self.language.name + ' ' + self.version
