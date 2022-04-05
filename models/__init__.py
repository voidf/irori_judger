from mongoengine import connect
from config.env import db_auth
connect(host=db_auth)

from models.user import *
from models.comment import *
from models.problem import *
from models.submission import *
from models.runtime import *
from models.contest import *
