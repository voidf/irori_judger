import datetime
import json
import traceback
import os
import re
import requests
from flask import Blueprint
from flask import current_app as flaskapp
from flask import g, jsonify, request
from mongoengine.queryset.visitor import Q

from app.api import handle_error, verify_params, master_auth
from app.common.result import falseReturn, trueReturn

from app.util.time import get_beijing_time, get_time_range_by_day, ts2beijing
from app import db
import xlrd
import base64


def continue_handler(usr,l:list,s:int,j:dict,is_first_arrive:bool, progress:str=usr.progress) -> list:
    """
    处理continue和jump事件的方法

    这些事件无需交互可以一路往下

    但完成后要用misc_handler来防止wait事件没有被执行

    j为当前章节文件反序列化后的字典

    s为待判定事件下标
    """
    
    while j[progress][s]['action'] == 'continue' or j[progress][s]['action'] == 'jump':
        
        if j[progress][s]['typ']=='I':
            with open('app/img/'+j[progress][s]['msg'],'rb') as f:
                j[progress][s]['msg'] = base64.b64encode(f.read()).decode('utf-8')

        j[progress][s]['msg'] = msg_replacer(usr,j[progress][s]['msg'])
        l.append(j[progress][s])

        if j[progress][s]['action'] == 'jump':
            usr,s,j,progress = event_updater(usr,j[progress][s]['to'],j,s)
            continue

        if 'MORE' in j[progress][s]:
            usr,s,j,progress = event_updater(usr,j[progress][s]['MORE'],j,s)
            continue
        is_first_arrive = False
        s+=1
    return misc_handler(usr,l,s,j,is_first_arrive)

def misc_handler(usr,l:list,s:int,j:dict,is_first_arrive:bool) -> list:
    """
    处理各种非continue和jump事件的方法

    由于这些事件必定会要求用户交互

    所以只在目前消息链l没有东西的时候做

    j为当前章节文件反序列化后的字典

    s为待判定事件下标
    """
    if j[usr.progress][s]['typ']=='I':
        with open('app/img/'+j[usr.progress][s]['msg'],'rb') as f:
            j[usr.progress][s]['msg'] = base64.b64encode(f.read()).decode('utf-8')
    if is_first_arrive: # 是这个事件已经被做完的时候
        is_first_arrive = False
        print('此时没有continue')
        
        act = j[usr.progress][s]['action']

        if act == 'input':
            if 'args' in g.data and g.data['args']:
                dd = {f'''set__{j[usr.progress][usr.ind]['kw']}''': g.data['args'][:512]}
                usr.update(**dd)
                usr = User.objects(qq=g.data['qq']).first()
                s += 1

            else:
                return [{
                            "typ": "P",
                            "msg": "【提示】请随便输入一些什么字符串但是得有输入",
                            "delays": 0,
                            "action": "FIN"
                        }]
        elif act == 'wait':
            if get_beijing_time() - usr.last_time_event_begins >= datetime.timedelta(seconds=j[usr.progress][usr.ind]['length']):
                l.append(j[usr.progress][s].get('done',{}))
                usr,s,j,pgs = event_updater(usr,j[usr.progress][s].get('done',{}),j,s)

            else:
                return [{
                            "typ": "P",
                            "msg": "目前无法进行任何操作",
                            "delays": 0,
                            "action": "FIN"
                        }]
        elif act == 'query':
            if 'args' in g.data and g.data['args']:
                if 'equal' in j[usr.progress][s]:
                    l.append(j[usr.progress][s]['equal'].get(g.data['args'],j[usr.progress][s]['equal']['=[DEFAULT]=']))
                    usr,s,j,pgs = event_updater(usr,j[usr.progress][s]['equal'].get(g.data['args'],j[usr.progress][s]['equal']['=[DEFAULT]=']),j,s)

            else:
                return [{
                            "typ": "P",
                            "msg": "【提示】这是一个问题，得回答些什么",
                            "delays": 0,
                            "action": "FIN"
                        }]
        elif act == 'interact':
            if 'args' in g.data and g.data['args']:
                s += 1

            else:
                return [{
                            "typ": "P",
                            "msg": "【提示】说点什么？",
                            "delays": 0,
                            "action": "FIN"
                        }]
        elif act == 'select':
            if 'args' in g.data and g.data['args']:
                c = None
                print(j[usr.progress][s])
                for i in j[usr.progress][s]['match'].keys():
                    if i.upper() in g.data['args'].upper():
                        if c is None:
                            c = j[usr.progress][s]['match'][i]
                        else:
                            if c!=j[usr.progress][s]['match'][i]:
                                return [{
                                    "typ": "P",
                                    "msg": "【错误】不明确的选项%s"%g.data['args'],
                                    "delays": 0,
                                    "action": "FIN"
                                }]
                if c:
                    # print(c)
                    l.append(c)
                    usr,s,j,pgs = event_updater(usr,c,j,s)
                    # print(j[s])
                else:
                    return [{
                                "typ": "P",
                                "msg": "【错误】没有这样的选项%s"%g.data['args'],
                                "delays": 0,
                                "action": "FIN"
                            }]

            else:
                return [{
                            "typ": "P",
                            "msg": "【提示】这是一个选择肢",
                            "delays": 0,
                            "action": "FIN"
                        },j[usr.progress][s]]
        else:
            j[usr.progress][s]['msg'] = msg_replacer(usr,j[usr.progress][s]['msg'])
            return [j[usr.progress][s]]
            
        return continue_handler(usr,l,s,j,is_first_arrive) # 如果不操作l，可能死循环
    
    j[usr.progress][s]['msg'] = msg_replacer(usr,j[usr.progress][s]['msg'])
    l.append(j[usr.progress][s])
    print(l)
    if l and j[usr.progress][s]['action'] == 'wait': # 第一次到达wait事件
        print('Time Updated =======>')
        usr.update(last_time_event_begins=get_beijing_time())
        l.append(j[usr.progress][s].get('before',{}))
        event_updater(usr,j[usr.progress][s].get('before',{}),j,s)

    
    usr.update(ind=s)
    return l

def convert_xlsx(book_dir:str) -> dict:
    book = xlrd.open_workbook(book_dir)
    js = {}
    for name,sheetobj in zip(book.sheet_names(),book.sheets()):
        js.setdefault(name,[])
        
        for c in range(1,sheetobj.nrows):
            row = sheetobj.row(c)
            # print(row)
            cur = {
                'typ': row[0].value if row[0].value else 'P',
                'msg': row[1].value,
                'action': row[2].value if row[2].value else 'continue'
            }
            try:
                if row[3].value:
                    cur['note'] = row[3].value
            except:
                print('不重要：',traceback.format_exc())
            try:
                if row[4].value:
                    if row[4].ctype == 2:
                        cur['to'] = {"next":{"ind":int(row[4].value)-2}}
                    else:
                        cur['to'] = {"next":json.loads(row[4].value)}
                        if 'ind' in cur['to']:
                            cur['to']['ind']-=2
            except:
                print('不重要：',traceback.format_exc())
            try:
                if row[5].value:
                    cur['MORE'] = json.loads(row[5].value)
            except:
                print('不重要：',traceback.format_exc())
            try:
                if row[6].value:
                    cur[row[6].value] = {}
                    for branch in range(7,len(row),3):
                        if not row[branch].value:
                            break
                        if row[branch+1].ctype == 2:
                            jumpto = {
                                "ind":int(row[branch+1].value)-2
                            }
                        else:
                            jumpto = json.loads(row[branch+1].value)

                        for sniff_keys in row[branch].value.split(','):
                            cur[row[6].value][sniff_keys] = {}
                            if row[branch+2].value:
                                cur[row[6].value][sniff_keys].update(json.loads(row[branch+2].value))
                            cur[row[6].value][sniff_keys].update({"next":jumpto})
            except:
                print('不重要：',traceback.format_exc())

            js[name].append(cur)
    return js

class CheckPoint(db.EmbeddedDocument):
    stage = db.StringField(default='1-1')
    progress = db.StringField(default='1-1-0')
    ind = db.IntField(default=0)
    kizuna_event = db.ListField(db.StringField(),default=[])
    kizuna = db.IntField(default=0)
    quests = db.ListField(db.StringField(),default=[])
    solved = db.ListField(db.StringField(),default=[])

    score  = db.IntField(default=0)
    bitcoin = db.FloatField(default=0.0)
    vdate = db.DateTimeField(default=datetime.datetime(2030,3,5))

    def exec_recover(self) -> dict:
        return {
            'stage':self.stage,
            'progress':self.progress,
            'ind':self.ind,
            'kizuna_event':self.kizuna_event,
            'kizuna':self.kizuna,
            'quests':self.quests,
            'solved':self.solved,
            'score':self.score,
            'bitcoin':self.bitcoin,
            'vdate':self.vdate
        }

    def get_json(self) -> str:
        """回来的是json的字 符 串，可以被loads"""
        return self.to_json()

class User(db.Document): #标井号的不能给用户看
    qq = db.IntField() #
    kizuna = db.IntField(default=0) #
    
    check_point = db.MapField(db.EmbeddedDocumentField(CheckPoint),default={})
    stage = db.StringField(default='1-1') #
    progress = db.StringField(default='1-1-0') #
    ind = db.IntField(default=0) #
    player_name = db.StringField(default='伊吕利')
    kizuna_event = db.ListField(db.StringField(),default=[])
    quests = db.ListField(db.StringField(),default=[])
    solved = db.ListField(db.StringField(),default=[])
    stories = db.ListField(db.StringField(),default=[])
    watched = db.ListField(db.StringField(),default=[])
    score  = db.IntField(default=0)
    bitcoin = db.FloatField(default=0.0)

    features = db.ListField(db.StringField(),default=[])
    menus = db.ListField(db.StringField(),default=[])
    last_login = db.DateTimeField(default=get_beijing_time())
    last_time_event_begins = db.DateTimeField()
    vdate = db.DateTimeField(default=datetime.datetime(2030, 4, 12))

    def get_check_point(self) -> dict:
        return {
            'stage':self.stage,
            'progress':self.progress,
            'ind':self.ind,
            'kizuna_event':self.kizuna_event,
            'kizuna':self.kizuna,
            'quests':self.quests,
            'solved':self.solved,
            'score':self.score,
            'bitcoin':self.bitcoin,
            'vdate':self.vdate
        }

    def get_json(self) -> dict:
        return {
            'qq': self.qq,
            'stage': self.stage,
            'ind': self.ind,
            'check_point':self.check_point,
            'progress': self.progress,
            'solved': self.solved,
            'score': self.score,
            'bitcoin': self.bitcoin,
            'last_login': self.last_login,
            'last_time_event_begins': self.last_time_event_begins,
            'quests': self.quests,
            'kizuna_event':self.kizuna_event,
            'stories': self.stories,
            'kizuna': self.kizuna,
            'watched':self.watched,
            'player_name': self.player_name,
            'features': self.features,
            'menus':self.menus,
            'vdate':self.vdate
        }

    def insert_user(qq, last_login, **kwargs):
        return User(qq=qq,
                    last_login=last_login,
                    kizuna=0,
                    progress='1-1-0',
                    stage='1-1',
                    ind=0,
                    vdate=datetime.datetime(2030, 4, 12),
                    menus=[],
                    features=[]).save()

    def update_or_create(**kwargs):
        _t = User.objects(qq=int(kwargs['qq']))
        if len(_t):
            return _t.update(**kwargs)
        else:
            return User.insert_user(**kwargs)

def event_updater(o:User, d:dict, j:dict, s:int, progress:str=usr.progress) -> tuple:
    """
    先做完本事件的其他事情再调用此函数更新状态

    更新用户当前状态，返回处理后的四要素，注意下标会重定向

    记得跑过以后更新一次当前数据库对象
    """

    for n in d.get('new',[]):
        o.update(add_to_set__menus=n)
    for n in d.get('newFeatures',[]):
        o.update(add_to_set__features=n)
    for n in d.get('stories',[]):
        o.update(add_to_set__stories=n)
    for n in d.get('quests',[]):
        o.update(add_to_set__quests=n)

    changed_progress_flg = False
    o.score += d.get('score',0)
    o.bitcoin += d.get('bitcoin',0)
    o.save()
    if 'virtual_date' in d:
        o.update(vdate = o.vdate+datetime.timedelta(days=d['virtual_date']))

    if 'kizuna' in d:
        if o.progress + ':' + str(o.ind) not in o.kizuna_event:
            o.update(kizuna=o.kizuna + d['kizuna'],add_to_set__kizuna_event = o.progress + ':' + str(o.ind))
    
    if 'next' in d:
        if 'stage' in d['next'] or 'progress' in d['next']:
            changed_progress_flg = True
        if 'stage' in d['next']:
            o = User.objects(qq=o.qq).first()
            o.ind = d['next'].get('ind',0)
            o.progress = d['next'].get('progress',o.progress)
            o.stage=d['next'].get('stage',o.stage)
            if o.stage not in o.check_point:
                o.check_point[o.stage] = CheckPoint(**o.get_check_point())
            o.save()
            s = o.ind
            with open(f'app/plot/{o.stage}.json','r') as fr:
                j = json.load(fr)
        else:
            o = User.objects(qq=o.qq).first()
            o.ind = d['next'].get('ind',0)
            o.progress = d['next'].get('progress',o.progress)
            o.save()
            s = o.ind
    else:
        s+=1

    o = User.objects(qq=o.qq).first()
    if changed_progress_flg:
        return o,s,j,o.progress
    else:
        return o,s,j,progress

def msg_replacer(o:User, s:str)->str:
    """
    现在只是替换用户名用
    """
    print(f"REPLACER {s}")
    for i in re.findall(r'\$<.*?>',s):
        print(f"{getattr(o,i[2:-1],'undefined')}")
        s = s.replace(i,getattr(o,i[2:-1],'undefined'))
    return s

def getDescriptionJson(prefix):
    if os.path.exists(prefix+'.json'):
        with open(prefix+'.json','r') as f:
            return json.load(f)
    elif os.path.exists(prefix+'.xlsx'):
        return convert_xlsx(prefix+'.xlsx')
    elif os.path.exists(prefix+'.xls'):
        return convert_xlsx(prefix+'.xls')
    else:return {}

domain_blueprint = Blueprint('domain', __name__, url_prefix='/domain')


@domain_blueprint.before_request
def before_request():
    try:
        if request.method == "POST" and request.get_data():
            g.data = request.get_json(silent=True)
        else:
            g.data = {}
    except:
        traceback.print_exc()
        return falseReturn(None, '数据错误')


@domain_blueprint.route('/ls', methods=['POST'])
@handle_error
@master_auth
def chkDB():
    print(User.objects())
    return trueReturn({'info': [_.get_json() for _ in User.objects()]})


@domain_blueprint.route('/cls', methods=['POST'])
@handle_error
@master_auth
def clearDB():
    for _ in User.objects():
        _.delete()
    return trueReturn()


@domain_blueprint.route('/setp', methods=['POST'])
@handle_error
@verify_params(params=['qq', 'args'])
def setp():
    qq = int(g.data['qq'])
    usr = User.objects(qq=qq).first()
    stage, progress, ind = g.data['args'].split(' ')
    ind = int(ind)
    print('【杀虫】',stage, progress, ind)
    User.update_or_create(qq=qq, 
                         last_login=get_beijing_time(),
                         stage=stage, 
                         progress=progress, 
                         ind=ind)
    return trueReturn()


@domain_blueprint.route('/init', methods=['POST'])
@handle_error
@verify_params(params=['qq'])
def init():
    qq = int(g.data['qq'])
    User.update_or_create(qq=qq,
                          last_login=get_beijing_time(),
                          kizuna=0,
                          progress='1-1-0',
                          stage='1-1',
                          ind=0,
                          vdate=datetime.datetime(2030, 4, 12),
                          menus=[],
                          features=[],
                          check_point={},
                          player_name = 'いろり',
                          kizuna_event = [],
                          quests = [],
                          solved = [],
                          stories = [],
                          watched = [],
                          score = 0,
                          bitcoin = 0.0
                          )
    usr = User.objects(qq=qq).first()

    usr.check_point['1-1-0'] = CheckPoint(**usr.get_check_point())
    usr.save()
    return trueReturn()

@domain_blueprint.route('/test', methods=['POST'])
@handle_error
@verify_params(params=['qq'])
def test():
    usr = User.objects(qq=int(g.data['qq'])).first()
    return trueReturn(usr.to_json())


@domain_blueprint.route('/insert', methods=['POST'])
@handle_error
@verify_params(params=['qq'])
def insert():
    qq = int(g.data['qq'])
    User.update_or_create(qq=qq, last_login=get_beijing_time())
    return trueReturn()

@domain_blueprint.route("/pull", methods=["POST"])
@handle_error
def pull():
    return trueReturn(msg=os.popen('git pull').read())

@domain_blueprint.route("/status", methods=["POST"])
@handle_error
@verify_params(params=['qq'])
def status():
    usr = User.objects(qq=int(g.data['qq'])).first()
    return trueReturn(data=usr.get_json())

@domain_blueprint.route("/save", methods=["POST"])
@handle_error
@verify_params(params=['qq','chkp'])
def saver():
    usr = User.objects(qq=int(g.data['qq'])).first()
    usr.check_point[g.data['chkp']] = CheckPoint(**usr.get_check_point())
    usr.save()
    return trueReturn()

@domain_blueprint.route("/story", methods=["POST"])
@handle_error
@verify_params(params=['qq','storyid'])
def story():
    usr = User.objects(qq=int(g.data['qq'])).first()
    qid = g.data['storyid']
    js = getDescriptionJson(f'app/story/{qid}')
    # with open(f'app/stages/{qid}.json','r') as fr:
    #     js = json.load(fr)
    # for p,k in enumerate(js['description']):
    #     if k.get('typ','P') == 'P':
    #         k['msg'] = msg_replacer(usr,k['msg'])
    #     elif k['typ'] == 'I':
    #         with open('app/stages/'+k['msg'],'rb') as f:
    #             js['description'][p]['msg'] = base64.b64encode(f.read()).decode('utf-8')
    if qid not in usr.watched:
        usr.update(add_to_set__watched=qid)
    print(js['description'])
    return trueReturn(data=continue_handler(usr,[],0,js,True,'description'))

@domain_blueprint.route("/quest", methods=["POST"])
@handle_error
@verify_params(params=['qq','questid'])
def quest():
    qid = g.data['questid']
    usr = User.objects(qq=int(g.data['qq'])).first()
    js = getDescriptionJson(f'app/quest/{qid}')
    return trueReturn(data=continue_handler(usr,[],0,js,True,'description'))

@domain_blueprint.route("/solve", methods=["POST"])
@handle_error
@verify_params(params=['qq','questid'])
def solve():
    qid = g.data['questid']
    qq = int(g.data['qq'])
    usr = User.objects(qq=qq).first()
    js = getDescriptionJson(f'app/quest/{qid}')
    # with open(f'app/stages/{qid}.json','r') as fr:
    #     js = json.load(fr)
    # if qid not in usr.solved:
    #     usr.update(add_to_set__solved=qid)
    #     event_updater(usr,js['done'],{},0)
    return trueReturn(data=continue_handler(usr,[],0,js,True,'done'))


@domain_blueprint.route("/recover", methods=["POST"])
@handle_error
@verify_params(params=['qq','progress'])
def recover():
    pro = g.data['progress']
    qq = int(g.data['qq'])
    usr = User.objects(qq=qq).first()
    if pro in usr.check_point:
        usr.update(**usr.check_point[pro].exec_recover())
        print(usr.to_json())
        return trueReturn()
    else:
        return trueReturn(msg='【错误】指定的存档点不存在')



@domain_blueprint.route("/asobi", methods=["POST"])
@handle_error
@verify_params(params=['qq'])
def asobi():

    if not User.objects(qq=g.data['qq']):
        init()

    usr = User.objects(qq=g.data['qq']).first()
    usr.update(last_login=get_beijing_time())
    js = getDescriptionJson(f'app/plot/{usr.stage}')
    # if os.path.exists(f'app/stages/{usr.stage}.json'):
    #     with open(f'app/stages/{usr.stage}.json','r') as fr:
    #         js = json.load(fr)
    # elif os.path.exists(f'app/stages/{usr.stage}.xlsx'):
    #     js = convert_xlsx(f'app/stages/{usr.stage}.xlsx')
    # else:
    #     return falseReturn(msg='不存在关卡文件')
    return trueReturn(data=continue_handler(usr,[],usr.ind,js,True))
