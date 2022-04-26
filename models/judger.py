from mongoengine.document import Document
from mongoengine.fields import *

class Judger(Document):
    """
    评测机的数据，用于认证评测机，查询在线状态等

    注意名字是主键，不能重名

    多worker环境塞内存不是好文明，所以还是把在线信息塞数据库
    """
    name = StringField(primary_key=True)
    created = DateTimeField()
    auth_key = StringField()
    is_blocked = BooleanField(default=False)
    online = BooleanField(default=False)
    start_time = DateTimeField()
    ping = FloatField()
    load = FloatField()
    desc = StringField()
    last_ip = StringField()
    problems = ListField(StringField()) # 此处不想整外键了
    runtimes = ListField(StringField())
    
    def __str__(self):
        return self.name
""" TODO
    def disconnect(self, force=False):
        disconnect_judge(self, force=force)

    disconnect.alters_data = True

    @classmethod
    def runtime_versions(cls):
        qs = (RuntimeVersion.objects.filter(judge__online=True)
              .values('judge__name', 'language__key', 'language__name', 'version', 'name')
              .order_by('language__key', 'priority'))

        ret = defaultdict(OrderedDict)

        for data in qs:
            judge = data['judge__name']
            key = data['language__key']
            if key not in ret:
                ret[judge][key] = {'name': data['language__name'], 'runtime': []}
            ret[judge][key]['runtime'].append((data['name'], (data['version'],)))

        return {judge: list(data.items()) for judge, data in ret.items()}

    @cached_property
    def uptime(self):
        return timezone.now() - self.start_time if self.online else 'N/A'

    @cached_property
    def ping_ms(self):
        return self.ping * 1000 if self.ping is not None else None

    @cached_property
    def runtime_list(self):
        return map(attrgetter('name'), self.runtimes.all())

    class Meta:
        ordering = ['name']
        verbose_name = _('judge')
        verbose_name_plural = _('judges')
"""