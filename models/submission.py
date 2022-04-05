from mongoengine.document import *
from mongoengine.fields import *
from mongoengine.queryset.base import *
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

class SubmissionTestCase(EmbeddedDocument):
    RESULT = SUBMISSION_RESULT

    case = IntField(verbose_name='test case ID')
    status = StringField(max_length=3, verbose_name='status flag', choices=SUBMISSION_RESULT)
    time = FloatField(verbose_name='execution time', )
    memory = FloatField(verbose_name='memory usage', )
    points = FloatField(verbose_name='points granted', )
    total = FloatField(verbose_name='points possible', )
    batch = IntField(verbose_name='batch number', )
    feedback = StringField(verbose_name='judging feedback')
    output = StringField(verbose_name='program output')


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
    
    meta = {'allow_inheritance': True}
    id = SequenceField(default=1, primary_key=True)
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



