import datetime

def utc2beijing(utc):
    dtl = datetime.timedelta(hours=8)
    return utc+dtl
    
def get_beijing_time():
    utc = datetime.datetime.utcnow()
    return utc2beijing(utc)

def get_time_range_by_day(day):
    #TODO 根据传入的时间，返回从前一天的24点到当天的24点的时间范围，
    yesterday = datetime.datetime()



def ts2beijing(timestamp):
    return utc2beijing(datetime.datetime.utcfromtimestamp(timestamp))