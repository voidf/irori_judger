from mongoengine import connect
from config import secret
connect(host=secret.db_auth)

from models.user import *
from models.comment import *
from models.problem import *
from models.submission import *
from models.runtime import *
from models.contest import *
