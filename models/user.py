from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
import hashlib
from config import secret

AUTHORITY_LEVEL = (
    (0, 'admin'),
    (1, 'operator'),
    (2, 'officer'),
    (3, 'default'),
    (4, 'guest'),
)

def encrypt(s: str) -> str:
    return hashlib.sha256((s + secret.auth_salt).encode('utf-8')).hexdigest()

# class Role(Document):
#     """OJ级别权限组"""
#     level = IntField(default=5)

class User(Document):
    """用户主体"""
    # 认证！（字正腔圆）
    handle = StringField(primary_key=True)
    password = StringField()
    email = EmailField()
    
    authority_level = IntField(default=3, choices=AUTHORITY_LEVEL) # 不使用传统的RBAC，权限只分：狗管理、OJ运维人员、一般出题人（类似cf教练）、一般用户、游客
    """
    鉴权目标：
        OJ钦定传人、开发人员掌握admin
        运维打杂退役老嘢掌握operator
        受信的老队员掌握officer
        一般通过用户掌握user

    """
    # 社交
    avatar = URLField()     # 头像url
    nick = StringField()    # 昵称
    desc = StringField()    # 这个人很懒.jpg

    last_access = DateTimeField()   # 上次登录
    last_ip = StringField()         # 上次ip

    rating = IntField(default=1500) # 留作后用
    solved = ListField(ReferenceField('Problem'))
    tried = ListField(ReferenceField('Problem'))

    api_token = StringField() # 注意维护唯一性

    def pw_chk(self, password: str) -> bool:
        return self.password == encrypt(password)

    def pw_set(self, password: str) -> "User":
        self.password = encrypt(password)
        return self

