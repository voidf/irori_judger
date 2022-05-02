from mongoengine import *
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import *
from models.comment import Comment
from models.mixin.reportable import Reportable
from models.mixin.expandable import Expandable, INVISIBLE
from mongoengine.queryset import *

# class ProblemCounter(Document):
#     """单例数据，维护Problem的id自增"""
#     cnt = LongField()
#     @classmethod
#     def init(cls):
#         if not cls.objects:
#             cls(cnt=1000).save()
    
#     @classmethod
#     def alloc(cls):
#         return cls.objects.modify(
#             new=False,
#             inc__cnt=1
#         ).cnt

# if __name__ == '__main__':
#     from mongoengine import connect
#     connect(host='mongodb://localhost:27017/testOJ')
#     ProblemCounter.init()
#     print(ProblemCounter.alloc())

from models.user import User

class Tag(Document, Expandable):
    """运维人员以上才能修改的Tag"""
    name = StringField(primary_key=True)
    color = IntField() # RGB色号

# PROBLEM_DIFFICULTIES = ()

class ProblemType(Document, Expandable):
    """问题种类，像交互题，spj题，经典题，提交答案题等等"""
    name = StringField(primary_key=True)
    color = IntField() # RGB代码
    help: INVISIBLE = StringField() # 有关这种问题类型的帮助文本，有可能很长所以invisible

class ProblemGroup(Document, Expandable):
    """问题组，像hdu的来源"""
    name = StringField(primary_key=True)
    full_name = StringField() # 可选的全名
    problems = ListField(LazyReferenceField('Problem'))
    

from models.runtime import Runtime

class SubmissionSourceAccess:
    """提交源代码可见性"""
    ALWAYS = 'A'    # 总是可见
    SOLVED = 'S'    # 解出后可见
    ONLY_OWN = 'O'  # 仅作者可见
    FOLLOW = 'F'    # 跟随全局设置

class LanguageLimit(EmbeddedDocument):
    language = LazyReferenceField(Runtime)
    time_limit = FloatField()
    memory_limit = IntField()

class Problem(Document, Expandable):
    SUBMISSION_SOURCE_ACCESS = (
        (SubmissionSourceAccess.FOLLOW, 'Follow global setting'),
        (SubmissionSourceAccess.ALWAYS, 'Always visible'),
        (SubmissionSourceAccess.SOLVED, 'Visible if problem solved'),
        (SubmissionSourceAccess.ONLY_OWN, 'Only own submissions'),
    )
    # id = SequenceField(default=1000, primary_key=True)
    code = StringField(primary_key=True) # 标题

    # 管理属性
    authors = ListField(
        LazyReferenceField(User, reverse_delete_rule=PULL),
    ) # 作者
    curators = ListField(
        LazyReferenceField(User, reverse_delete_rule=PULL),
    ) # 协作者
    is_public = BooleanField(default=False)
    date = DateTimeField() # public日期
    source_visibility = StringField(default=SubmissionSourceAccess.FOLLOW, choices=SUBMISSION_SOURCE_ACCESS)

    # 检索属性
    tags = ListField(ReferenceField(Tag, reverse_delete_rule=PULL))
    difficulty = IntField() # 大概什么分数段位的
    types = ListField(ReferenceField(ProblemType, reverse_delete_rule=PULL))
    group = ListField(LazyReferenceField(ProblemGroup, reverse_delete_rule=PULL))
    solved = IntField(default=0)
    submitted = IntField(default=0)

    # 判题属性
    time_limit = FloatField() # 秒
    memory_limit = IntField() # kb
    short_circuit = BooleanField() # 短路，遇到一个错的就停
    allowed_languages = ListField(LazyReferenceField(Runtime, reverse_delete_rule=PULL)) # 为空表示不限制

    # 比赛属性
    partial = BooleanField() # 是否有部分分


    # 题面数据什么的应该存文件里
    desc: INVISIBLE = StringField() # 描述
    title = StringField()
    DESC_TYPE = (
        ('M', 'Markdown'),
        ('L', 'LaTeX'),
        ('H', 'html'),
    )
    desc_type = StringField(choices=DESC_TYPE)

    language_limit = EmbeddedDocumentListField(LanguageLimit)

    discussion_handle = LazyReferenceField(Comment, reverse_delete_rule=DO_NOTHING)
    discussion_shown = BooleanField(default=True)

    solution_handle = LazyReferenceField(Comment, reverse_delete_rule=DO_NOTHING)
    solution_shown = BooleanField(default=True)

ProblemGroup.register_delete_rule(Problem, 'problems', PULL)




# class ProblemDiscuss(Document, Reportable):
#     """问题讨论区"""
#     poster = ReferenceField(Comment, reverse_delete_rule=CASCADE, primary_key=True)
#     problem = ReferenceField(Problem, reverse_delete_rule=CASCADE)

# class ProblemSolution(Document, Reportable):
#     """题解区"""
#     poster = ReferenceField(Comment, reverse_delete_rule=CASCADE, primary_key=True)
#     problem = ReferenceField(Problem, reverse_delete_rule=CASCADE)


