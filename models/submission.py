from models.judger import Judger
from models.mixin.expandable import INVISIBLE, Expandable
from mongoengine.document import *
from mongoengine.fields import *
from mongoengine.queryset.base import *
from models.user import User
from models.problem import Problem
from models.runtime import Runtime
from config import static

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
    extended_feedback = StringField(verbose_name='extended judging feedback')
    output = StringField(verbose_name='program output')


class Submission(Document, Expandable):
    participation = ReferenceField('ContestParticipation', reverse_delete_rule=DO_NOTHING, null=True)
    is_pretested = BooleanField(default=False) # 是否跑过pretest

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
    id = SequenceField(primary_key=True)
    user = LazyReferenceField(User, reverse_delete_rule=CASCADE)
    problem = LazyReferenceField(Problem, reverse_delete_rule=CASCADE)
    language = LazyReferenceField(Runtime, reverse_delete_rule=CASCADE)
    date = DateTimeField() # 提交日期

    time = FloatField()
    memory = FloatField()
    points = FloatField() # 赋分，显示为的分数，考虑到有时候需要手动判错

    status = StringField(default='QU', choices=STATUS)
    result = StringField(choices=SUBMISSION_RESULT)

    error = StringField() # 编译错误信息
    current_testcase = IntField(default=0) # 当前用例

    batch = BooleanField(default=False) # 是否子任务
    cases = EmbeddedDocumentListField(SubmissionTestCase)
    case_points = FloatField(default=0) # case实际分数
    case_total = FloatField(default=0)  # case总分

    rejudge_date = DateTimeField()
    judged_date = DateTimeField()
    judged_on = ReferenceField(Judger) # 在哪台机子上评测

    source: INVISIBLE = StringField(max_length=static.source_code_limit)

    # is_pretested = BooleanField()

    @classmethod
    def get_id_secret(cls, sub_id):
        return str(sub_id)
        # return (hmac.new(utf8bytes(settings.EVENT_DAEMON_SUBMISSION_KEY), b'%d' % sub_id, hashlib.sha512)
        #             .hexdigest()[:16] + '%08x' % sub_id)

