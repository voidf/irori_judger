from mongoengine import *
from typing import Optional, TypeVar, Union, get_type_hints
import datetime
from mongoengine.fields import *
from mongoengine.pymongo_support import *
from mongoengine.context_managers import *
from mongoengine.document import *
from models.mixin.chkable import Chkable

INVISIBLE = TypeVar('INVISIBLE')

class Expandable(Chkable):
    """
    递归地解引用展开Mixin类，不能处理成环情况，与mongoengine.document.Document搭配使用
    
    或者叫自动拼表？
    """
    @staticmethod
    def expand_mono(obj):
        if hasattr(obj, 'get_base_info'):
            return getattr(obj, 'get_base_info')()
        else:
            return obj
    def get_base_info(self, *args):
        try:
            d = {}
            for k in self._fields_ordered:
                if get_type_hints(self).get(k, None) == INVISIBLE:
                    continue
                selfk = getattr(self, k)
                if isinstance(selfk, list):
                    for i in selfk:
                        d.setdefault(k, []).append(Expandable.expand_mono(i))
                else:
                    d[k] = Expandable.expand_mono(selfk)
            d['id'] = str(self.id)
            return d
        except: # 不加注解上面会报错
            return self.get_all_info()
    def get_all_info(self, *args):
        d = {} 
        for k in self._fields_ordered:
            selfk = getattr(self, k)
            if isinstance(selfk, list):
                for i in selfk:
                    d.setdefault(k, []).append(Expandable.expand_mono(i))
            else:
                d[k] = Expandable.expand_mono(selfk)
        if hasattr(self, 'id'):
            d['id'] = str(self.id)
        return d


class SaveTimeExpandable(Expandable):
    create_time = DateTimeField()
    def save_changes(self):
        return self.save()
    def first_create(self):
        self.create_time = datetime.datetime.now()
        return self.save_changes()
    
    def get_base_info(self, *args):
        d = super().get_base_info(*args)
        d['create_time'] = self.create_time.strftime('%Y-%m-%d')
        return d

    def get_all_info(self, *args):
        d = super().get_all_info(*args)
        d['create_time'] = self.create_time.strftime('%Y-%m-%d')
        return d
