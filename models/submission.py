from mongoengine import *
from mongoengine.document import Document
from models.user import User
from models.problem import Problem
from models.runtime import Runtime

SUBMISSION_RESULT = (
    ('AC', 'Accepted'),
    ('WA', 'Wrong Answer'),
    ('TLE', 'Time Limit Exceeded'),
    ('MLE', 'Memory Limit Exceeded'),
    ('OLE', 'Output Limit Exceeded'),
    ('IR', 'Invalid Return'),
    ('RTE', 'Runtime Error'),
    ('CE', 'Compile Error'),
    ('IE', 'Internal Error'),
    ('SC', 'Short circuit'),
    ('AB', 'Aborted'),
)

class Submission(Document):
    STATUS = (
        ('QU', 'Queued'),
        ('P', 'Processing'),
        ('G', 'Grading'),
        ('D', 'Completed'),
        ('IE', 'Internal Error'),
        ('CE', 'Compile Error'),
        ('AB', 'Aborted'),
    )
    IN_PROGRESS_GRADING_STATUS = ('QU', 'P', 'G')
    RESULT = SUBMISSION_RESULT
    USER_DISPLAY_CODES = {
        'AC': 'Accepted',
        'WA': 'Wrong Answer',
        'SC': 'Short Circuited',
        'TLE': 'Time Limit Exceeded',
        'MLE': 'Memory Limit Exceeded',
        'OLE': 'Output Limit Exceeded',
        'IR': 'Invalid Return',
        'RTE': 'Runtime Error',
        'CE': 'Compile Error',
        'IE': 'Internal Error (judging server error)',
        'QU': 'Queued',
        'P': 'Processing',
        'G': 'Grading',
        'D': 'Completed',
        'AB': 'Aborted',
    }
    meta = {'allow_inheritance': True}
    user = ReferenceField(User, reverse_delete_rule=CASCADE)
    problem = ReferenceField(Problem, reverse_delete_rule=CASCADE)
    language = ReferenceField(Runtime, reverse_delete_rule=CASCADE)
    date = DateTimeField()

    time = FloatField()
    memory = FloatField()
    points = FloatField()

    status = StringField(default='QU', choices=STATUS)
    result = StringField(choices=SUBMISSION_RESULT)

    error = StringField() # 编译错误信息
    current_testcase = IntField(default=0) # 当前用例

    # batch = BooleanField(default=False) # 是否子任务
    case_points = FloatField(default=0) # case分数
    # case_total = FloatField(default=0)  # case总分

    judge_date = DateTimeField()
    rejudge_date = DateTimeField()

    # is_pretested = BooleanField()



