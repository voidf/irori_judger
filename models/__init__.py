from mongoengine import connect
from config import secret
connect(host=secret.db_auth)

from models.problem import *
from models.user import *
from models.comment import *
from models.submission import *
from models.runtime import *
from models.contest import *

User.register_delete_rule(Problem, 'solved', PULL)
User.register_delete_rule(Problem, 'tried', PULL)
