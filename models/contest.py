from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.comment import Comment
from models.user import User
from models.problem import Problem
from models.submission import Submission

class ContestProblem(Document):
    """比赛状态的问题"""
    problem = ReferenceField(Problem, reverse_delete_rule=CASCADE)
    points = FloatField() # IOI用赋分
    partial = BooleanField(default=True)
    is_pretested = BooleanField(default=False)
    max_submissions = IntField() # 提交次数限制


class Contest(Document):
    """比赛"""
    SCOREBOARD_VISIBLE = 'V'
    SCOREBOARD_AFTER_CONTEST = 'C'
    SCOREBOARD_AFTER_PARTICIPATION = 'P'
    SCOREBOARD_HIDDEN = 'H'
    SCOREBOARD_VISIBILITY = (
        (SCOREBOARD_VISIBLE, 'Visible'),
        (SCOREBOARD_AFTER_CONTEST, 'Hidden for duration of contest'),
        (SCOREBOARD_AFTER_PARTICIPATION, 'Hidden for duration of participation'),
        (SCOREBOARD_HIDDEN, 'Hidden permanently'),
    )
    # meta = {'allow_inheritance': True}
    poster = ReferenceField(Comment, reverse_delete_rule=DO_NOTHING)

    id = StringField(primary_key=True)
    name = StringField()

    authors = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    curators = ListField(ReferenceField(User, reverse_delete_rule=PULL))

    problems = ListField(ReferenceField(ContestProblem, reverse_delete_rule=PULL))
    
    start_time = DateTimeField()
    end_time = DateTimeField()

    is_visible = BooleanField(default=False) # 在比赛list中展示
    is_rated = BooleanField(default=False)
    rate_all = BooleanField(default=False)
    rating_floor = IntField()
    rating_ceiling = IntField()

    run_pretests_only = BooleanField(default=False)

    is_private = BooleanField(default=False) # 是否带密码
    access_code = StringField() # 访问密码

class ContestParicipation(Document):
    """用户的比赛注册信息"""
    contest = ReferenceField(Contest, reverse_delete_rule=CASCADE)
    user = ReferenceField(User, reverse_delete_rule=CASCADE)

    score = FloatField(default=0) # 分数 赛时检索用
    cumtime = FloatField(default=0) # 罚时

    is_disqualified = BooleanField(default=False) # 是否被取消资格/打星
    virtual = IntField(default=0) # 0表示正常参赛，1以上表示第几轮VP

    format_data = DictField() # 留作后用

class ContestSubmission(Submission):
    participation = ReferenceField(ContestParicipation, reverse_delete_rule=CASCADE)
    points = FloatField
    is_pretest = BooleanField(default=False) # 是否只跑pretest

class Rating(Document):
    participation = ReferenceField(ContestParicipation, reverse_delete_rule=CASCADE)
    rank = IntField()
    rating = IntField()

