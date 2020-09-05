import os

class Config():
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 19198
    MONGODB_SETTINGS = {
        'db': 'irori_OpenJudge',
        'host': 'mongodb://localhost:27017/irori_OpenJudge',
    }
    JWT_SECRET = "yarimasune"