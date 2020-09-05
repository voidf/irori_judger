class DevelopmentConfig():
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 19198
    MONGODB_SETTINGS = {
        'db': 'irori_OpenJudge',
        'host': 'mongodb://database:27017/irori_OpenJudge',
    }