class ProductionConfig():
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 19198
    MONGODB_SETTINGS = {
        'db': 'irori_OpenJudge',
        'host': 'mongodb://database/irori_OpenJudge',
    }