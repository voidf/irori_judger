import datetime
import traceback
from models.runtime import Runtime
from network.misc import *
from network.zlib_packet_handler import ZlibPacketHandler
import asyncio
from network.judge_list import JudgeList
from loguru import logger
from collections import deque
import json
import logging
json_log = logging.getLogger('judge.json.bridge')
from models.submission import Submission
from models.contest import ContestSubmission
from models.problem import LanguageLimit
from collections import namedtuple

SubmissionData = namedtuple(
    'SubmissionData', 'time memory short_circuit pretests_only contest_no attempt_no user_id')


def _ensure_connection():
    pass
    # try:
    #     db.connection.cursor().execute('SELECT 1').fetchall()
    # except Exception:
    #     db.connection.close()

class JudgeHandler(ZlibPacketHandler):
    # proxies = proxy_list(settings.BRIDGED_JUDGE_PROXIES or [])
    proxies = proxy_list([])



    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, judge_list: JudgeList):
        super().__init__(reader, writer)

        self.judges = judge_list
        self.handlers = {
            'grading-begin': self.on_grading_begin,
            'grading-end': self.on_grading_end,
            'compile-error': self.on_compile_error,
            'compile-message': self.on_compile_message,
            'batch-begin': self.on_batch_begin,
            'batch-end': self.on_batch_end,
            # 'test-case-status': self.on_test_case,
            'internal-error': self.on_internal_error,
            'submission-terminated': self.on_submission_terminated,
            'submission-acknowledged': self.on_submission_acknowledged,
            'ping-response': self.on_ping_response,
            'supported-problems': self.on_supported_problems,
            'handshake': self.on_handshake,
        }
        self._working = False
        self._no_response_job = None
        self._problems = []
        self.executors = {}
        self.problems = {}
        self.latency = None
        self.time_delta = None
        self.load = 1e100
        self.name = None
        self.batch_id = None
        self.in_batch = False
        # self._stop_ping = threading.Event()
        self._stop_ping = asyncio.Event()
        # 1 minute average, just like load
        self._ping_average = deque(maxlen=6)
        self._time_delta = deque(maxlen=6)

        # each value is (updates, last reset)
        self.update_counter = {}
        self.judge = None
        self.judge_address = None

        self._submission_cache_id = None
        self._submission_cache = {}

    def on_connect(self):
        self.timeout = 15
        logger.info(f'Judge connected from: {self.client_address}')
        json_log.info(self._make_json_log(action='connect'))

    def on_disconnect(self):
        self._stop_ping.set()
        if self._working:
            logger.error(
                f'Judge {self.name} disconnected while handling submission {self._working}')
        self.judges.remove(self)
        if self.name is not None:
            self._disconnected()
        logger.info(
            f'Judge disconnected from: {self.client_address} with name {self.name}')

        json_log.info(self._make_json_log(
            action='disconnect', info='judge disconnected'))

        if self._working:
            # TODO
            # Submission.objects.filter(id=self._working).update(
                # status='IE', result='IE', error='')
            json_log.error(self._make_json_log(
                sub=self._working, action='close', info='IE due to shutdown on grading'))

    def _authenticate(self, id, key):
        # TODO
        # try:
        #     judge = Judge.objects.get(name=id, is_blocked=False)
        # except Judge.DoesNotExist:
        #     result = False
        # else:
        # result = hmac.compare_digest(judge.auth_key, key)
        result = True

        if not result:
            json_log.warning(self._make_json_log(
                action='auth', judge=id, info='judge failed authentication'))
        return result

    def _connected(self):
        # TODO
        # judge = self.judge = Judge.objects.get(name=self.name)
        # judge.start_time = timezone.now()
        # judge.online = True
        # judge.problems.set(Problem.objects.filter(
        #     code__in=list(self.problems.keys())))
        # judge.runtimes.set(Language.objects.filter(
        #     key__in=list(self.executors.keys())))

        # Delete now in case we somehow crashed and left some over from the last connection
        # RuntimeVersion.objects.filter(judge=judge).delete()
        # versions = []
        # for lang in judge.runtimes.all():
        #     versions += [
        #         RuntimeVersion(language=lang, name=name, version='.'.join(
        #             map(str, version)), priority=idx, judge=judge)
        #         for idx, (name, version) in enumerate(self.executors[lang.key])
        #     ]
        # RuntimeVersion.objects.bulk_create(versions)
        # judge.last_ip = self.client_address[0]
        # judge.save()
        self.judge_address = f'[{self.client_address[0]}]:{self.client_address[1]}'
        json_log.info(self._make_json_log(action='auth', info='judge successfully authenticated',
                                          executors=list(self.executors.keys())))

    def _disconnected(self):
        pass
        # TODO
        # Judge.objects.filter(id=self.judge.id).update(online=False)
        # RuntimeVersion.objects.filter(judge=self.judge).delete()

    def _update_ping(self):
        pass
        # TODO
        # try:
            # Judge.objects.filter(name=self.name).update(
                # ping=self.latency, load=self.load)
        # except Exception as e:
            # What can I do? I don't want to tie this to MySQL.
            # if e.__class__.__name__ == 'OperationalError' and e.__module__ == '_mysql_exceptions' and e.args[0] == 2006:
                # db.connection.close()

    async def send(self, data):
        await super().send(json.dumps(data, separators=(',', ':')))

    async def on_handshake(self, packet):
        if 'id' not in packet or 'key' not in packet:
            logger.warning(f'Malformed handshake: {self.client_address}')
            self.close()
            return

        if not self._authenticate(packet['id'], packet['key']):
            logger.warning(f'Authentication failure: {self.client_address}')
            self.close()
            return

        self.timeout = 60
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        self.executors = packet['executors']
        for k, v in enumerate(self.executors):
            if not Runtime.objects(pk=k):
                Runtime(pk=v).save()
        
                
        self.name = packet['id']

        await self.send({'name': 'handshake-success'})
        logger.info(f'Judge authenticated: {self.client_address} ({packet["id"]})')
        self.judges.register(self)
        # threading.Thread(target=self._ping_thread).start()
        asyncio.ensure_future(self._ping_thread())
        self._connected()

    def can_judge(self, problem, executor, judge_id=None):
        return problem in self.problems and executor in self.executors and (not judge_id or self.name == judge_id)

    @property
    def working(self):
        return bool(self._working)

    def get_related_submission_data(self, submission) -> SubmissionData:
        # TODO
        
        # _ensure_connection()

        # try:
        #     s = ContestSubmission.objects(pk=submission).first()
        #     if s:
        #         pa = s.participation
        #         is_pretested = s.is_pretest
        #         part_virtual = pa.virtual
        #         part_id = pa.pk
        #     else:
        #         is_pretested = False
        #         part_virtual = None
        #         part_id = None
        #         s = Submission.objects.get(pk=submission)

        #     p = s.problem

        #     pid, time, memory, short_circuit = p.pk, p.time_limit, p.memory_limit, p.short_circuit
        #     lid = s.language.pk
        #     sub_date = s.date
        #     uid = s.user.pk
            
        #     # pid, time, memory, short_circuit, lid, is_pretested, sub_date, uid, part_virtual, part_id = (
        #     #     Submission.objects.filter(id=submission)
        #     #               .values_list('problem__id', 'problem__time_limit', 'problem__memory_limit',
        #     #                            'problem__short_circuit', 'language__id', 'is_pretested', 'date', 'user__id',
        #     #                            'contest__participation__virtual', 'contest__participation__id')).get()

        # except Submission.DoesNotExist:
        #     logger.error('Submission vanished: %s', submission)
        #     json_log.error(self._make_json_log(
        #         sub=self._working, action='request',
        #         info='submission vanished when fetching info',
        #     ))
        #     return

        # attempt_no = ContestSubmission.objects(problem__id=pid, participation__id=part_id, user__id=uid,
        #                                        date__lt=sub_date).exclude(status__in=('CE', 'IE')).count() + 1

        # try:
        #     time, memory = (LanguageLimit.objects.filter(problem__id=pid, language__id=lid)
        #                     .values_list('time_limit', 'memory_limit').get())
        # except LanguageLimit.DoesNotExist:
        #     pass

        # return SubmissionData(
        #     time=time,
        #     memory=memory,
        #     short_circuit=short_circuit,
        #     pretests_only=is_pretested,
        #     contest_no=part_virtual,
        #     attempt_no=attempt_no,
        #     user_id=uid,
        # )
        
        return SubmissionData(
            time=1,
            memory=512 * 1024,
            short_circuit=False,
            pretests_only=False,
            contest_no=1,
            attempt_no=1,
            user_id=1,
        )

    def disconnect(self, force=False):
        if force:
            # Yank the power out.
            self.close()
        else:
            self.send({'name': 'disconnect'})

    async def submit(self, id, problem, language, source):
        """应该在外部先创建好了对应的Submission数据库文档后再调用"""
        data = self.get_related_submission_data(id)
        self._working = id
        # self._no_response_job = threading.Timer(20, self._kill_if_no_response)
        self._no_response_job = asyncio.ensure_future(self._kill_if_no_response())
        await self.send({
            'name': 'submission-request',
            'submission-id': id,
            'problem-id': problem,
            'language': language,
            'source': source,
            'time-limit': data.time,
            'memory-limit': data.memory,
            'short-circuit': data.short_circuit,
            'meta': {
                'pretests-only': data.pretests_only,
                'in-contest': data.contest_no,
                'attempt-no': data.attempt_no,
                'user': data.user_id,
            },
        })

    async def _kill_if_no_response(self):
        await asyncio.sleep(20)
        logger.error(f'Judge failed to acknowledge submission: {self.name}: {self._working}')
        self.close()

    def on_timeout(self):
        if self.name:
            logger.warning(f'Judge seems dead: {self.name}: {self._working}')

    def malformed_packet(self, exception):
        logger.exception(f'Judge sent malformed packet: {self.name}')
        super(JudgeHandler, self).malformed_packet(exception)

    def on_submission_processing(self, packet):
        # TODO
        # _ensure_connection()

        id = packet['submission-id']
        # if Submission.objects.filter(id=id).update(status='P', judged_on=self.judge):
        #     event.post('sub_%s' % Submission.get_id_secret(
        #         id), {'type': 'processing'})
        #     self._post_update_submission(id, 'processing')
        #     json_log.info(self._make_json_log(packet, action='processing'))
        # else:
        #     logger.warning('Unknown submission: %s', id)
        #     json_log.error(self._make_json_log(
        #         packet, action='processing', info='unknown submission'))

    def on_submission_wrong_acknowledge(self, packet, expected, got):
        json_log.error(self._make_json_log(
            packet, action='processing', info='wrong-acknowledge', expected=expected))
        # TODO
        # Submission.objects.filter(id=expected).update(
        #     status='IE', result='IE', error=None)
        # Submission.objects.filter(id=got, status='QU').update(
        #     status='IE', result='IE', error=None)

    async def on_submission_acknowledged(self, packet):
        if not packet.get('submission-id', None) == self._working:
            logger.error(f'Wrong acknowledgement: {self.name}: {packet.get("submission-id", None)}, expected: {self._working}')
            self.on_submission_wrong_acknowledge(
                packet, self._working, packet.get('submission-id', None))
            self.close()
        logger.info(f'Submission acknowledged: {self._working}')
        if self._no_response_job:
            self._no_response_job.cancel()
            self._no_response_job = None
        self.on_submission_processing(packet)

    async def abort(self):
        await self.send({'name': 'terminate-submission'})

    def get_current_submission(self):
        return self._working or None

    async def ping(self):
        await self.send({'name': 'ping', 'when': datetime.datetime.now().timestamp()})

    async def on_packet(self, data):
        try:
            try:
                data = json.loads(data)
                if 'name' not in data:
                    raise ValueError
            except ValueError:
                self.on_malformed(data)
            else:
                handler = self.handlers.get(data['name'], self.on_malformed)
                await handler(data)
        except Exception:
            logger.exception(f'Error in packet handling (Judge-side): {self.name}')
            self._packet_exception()
            traceback.print_exc()
            # You can't crash here because you aren't so sure about the judges
            # not being malicious or simply malforms. THIS IS A SERVER!

    def _packet_exception(self):
        json_log.exception(self._make_json_log(sub=self._working, info='packet processing exception'))

    def _submission_is_batch(self, id):
        pass
        # TODO
        # if not Submission.objects.filter(id=id).update(batch=True):
            # logger.warning('Unknown submission: %s', id)

    async def on_supported_problems(self, packet):
        logger.info(f'{self.name}: Updated problem list')
        self._problems = packet['problems']
        self.problems = dict(self._problems)
        if not self.working:
            self.judges.update_problems(self)
        # TODO
        # self.judge.problems.set(Problem.objects.filter(
            # code__in=list(self.problems.keys())))
        json_log.info(self._make_json_log(
            action='update-problems', count=len(self.problems)))

    async def on_grading_begin(self, packet):
        logger.info(f'{self.name}: Grading has begun on: {packet["submission-id"]}')
        self.batch_id = None
        """ TODO

        if Submission.objects.filter(id=packet['submission-id']).update(
                status='G', is_pretested=packet['pretested'], current_testcase=1,
                batch=False, judged_date=timezone.now()):
            SubmissionTestCase.objects.filter(
                submission_id=packet['submission-id']).delete()
            event.post('sub_%s' % Submission.get_id_secret(
                packet['submission-id']), {'type': 'grading-begin'})
            self._post_update_submission(
                packet['submission-id'], 'grading-begin')
            json_log.info(self._make_json_log(packet, action='grading-begin'))
        else:
            logger.warning('Unknown submission: %s', packet['submission-id'])
            json_log.error(self._make_json_log(
                packet, action='grading-begin', info='unknown submission'))
        """
    

    async def on_grading_end(self, packet):
        logger.info(f'{self.name}: Grading has ended on: {packet["submission-id"]}')
        self._free_self(packet)
        self.batch_id = None

        # TODO
        # try:
        #     submission = Submission.objects.get(id=packet['submission-id'])
        # except Submission.DoesNotExist:
        #     logger.warning('Unknown submission: %s', packet['submission-id'])
        #     json_log.error(self._make_json_log(
        #         packet, action='grading-end', info='unknown submission'))
        #     return

        time = 0
        memory = 0
        points = 0.0
        total = 0
        status = 0
        status_codes = ['SC', 'AC', 'WA', 'MLE', 'TLE', 'IR', 'RTE', 'OLE']
        batches = {}  # batch number: (points, total)

        # for case in SubmissionTestCase.objects.filter(submission=submission):
        #     time += case.time
        #     if not case.batch:
        #         points += case.points
        #         total += case.total
        #     else:
        #         if case.batch in batches:
        #             batches[case.batch][0] = min(
        #                 batches[case.batch][0], case.points)
        #             batches[case.batch][1] = max(
        #                 batches[case.batch][1], case.total)
        #         else:
        #             batches[case.batch] = [case.points, case.total]
        #     memory = max(memory, case.memory)
        #     i = status_codes.index(case.status)
        #     if i > status:
        #         status = i

        # for i in batches:
        #     points += batches[i][0]
        #     total += batches[i][1]

        # points = round(points, 1)
        # total = round(total, 1)
        # submission.case_points = points
        # submission.case_total = total

        # problem = submission.problem
        # sub_points = round(
        #     points / total * problem.points if total > 0 else 0, 3)
        # if not problem.partial and sub_points != problem.points:
        #     sub_points = 0

        # submission.status = 'D'
        # submission.time = time
        # submission.memory = memory
        # submission.points = sub_points
        # submission.result = status_codes[status]
        # submission.save()

        # json_log.info(self._make_json_log(
        #     packet, action='grading-end', time=time, memory=memory,
        #     points=sub_points, total=problem.points, result=submission.result,
        #     case_points=points, case_total=total, user=submission.user_id,
        #     problem=problem.code, finish=True,
        # ))

        # if problem.is_public and not problem.is_organization_private:
        #     submission.user._updating_stats_only = True
        #     submission.user.calculate_points()

        # problem._updating_stats_only = True
        # problem.update_stats()
        # submission.update_contest()

        # finished_submission(submission)

        # event.post('sub_%s' % submission.id_secret, {
        #     'type': 'grading-end',
        #     'time': time,
        #     'memory': memory,
        #     'points': float(points),
        #     'total': float(problem.points),
        #     'result': submission.result,
        # })
        # if hasattr(submission, 'contest'):
        #     participation = submission.contest.participation
        #     event.post('contest_%d' %
        #                participation.contest_id, {'type': 'update'})
        # self._post_update_submission(submission.id, 'grading-end', done=True)

    async def on_compile_error(self, packet):
        logger.info(f'{self.name}: Submission failed to compile: {packet["submission-id"]}')
        self._free_self(packet)
        # TODO

        # if Submission.objects.filter(id=packet['submission-id']).update(status='CE', result='CE', error=packet['log']):
        #     event.post('sub_%s' % Submission.get_id_secret(packet['submission-id']), {
        #         'type': 'compile-error',
        #         'log': packet['log'],
        #     })
        #     self._post_update_submission(
        #         packet['submission-id'], 'compile-error', done=True)
        #     json_log.info(self._make_json_log(packet, action='compile-error', log=packet['log'],
        #                                       finish=True, result='CE'))
        # else:
        #     logger.warning('Unknown submission: %s', packet['submission-id'])
        #     json_log.error(self._make_json_log(packet, action='compile-error', info='unknown submission',
        #                                        log=packet['log'], finish=True, result='CE'))

    async def on_compile_message(self, packet):
        logger.info(f'{self.name}: Submission generated compiler messages: {packet["submission-id"]}')

        # if Submission.objects.filter(id=packet['submission-id']).update(error=packet['log']):
        #     event.post('sub_%s' % Submission.get_id_secret(
        #         packet['submission-id']), {'type': 'compile-message'})
        #     json_log.info(self._make_json_log(
        #         packet, action='compile-message', log=packet['log']))
        # else:
        #     logger.warning('Unknown submission: %s', packet['submission-id'])
        #     json_log.error(self._make_json_log(packet, action='compile-message', info='unknown submission',
        #                                        log=packet['log']))

    async def on_internal_error(self, packet):
        try:
            raise ValueError('\n\n' + packet['message'])
        except ValueError:
            logger.exception(f'Judge {self.name} failed while handling submission {packet["submission-id"]}')
        self._free_self(packet)

        id = packet['submission-id']
        # if Submission.objects.filter(id=id).update(status='IE', result='IE', error=packet['message']):
        #     event.post('sub_%s' % Submission.get_id_secret(
        #         id), {'type': 'internal-error'})
        #     self._post_update_submission(id, 'internal-error', done=True)
        #     json_log.info(self._make_json_log(packet, action='internal-error', message=packet['message'],
        #                                       finish=True, result='IE'))
        # else:
        #     logger.warning('Unknown submission: %s', id)
        #     json_log.error(self._make_json_log(packet, action='internal-error', info='unknown submission',
        #                                        message=packet['message'], finish=True, result='IE'))

    async def on_submission_terminated(self, packet):
        logger.info(f'{self.name}: Submission aborted: {packet["submission-id"]}')
        self._free_self(packet)

        # if Submission.objects.filter(id=packet['submission-id']).update(status='AB', result='AB', points=0):
        #     event.post('sub_%s' % Submission.get_id_secret(
        #         packet['submission-id']), {'type': 'aborted-submission'})
        #     self._post_update_submission(
        #         packet['submission-id'], 'terminated', done=True)
        #     json_log.info(self._make_json_log(
        #         packet, action='aborted', finish=True, result='AB'))
        # else:
        #     logger.warning('Unknown submission: %s', packet['submission-id'])
        #     json_log.error(self._make_json_log(packet, action='aborted', info='unknown submission',
        #                                        finish=True, result='AB'))

    async def on_batch_begin(self, packet):
        logger.info(f'{self.name}: Batch began on: {packet["submission-id"]}')
        self.in_batch = True
        if self.batch_id is None:
            self.batch_id = 0
            self._submission_is_batch(packet['submission-id'])
        self.batch_id += 1

        json_log.info(self._make_json_log(
            packet, action='batch-begin', batch=self.batch_id))

    async def on_batch_end(self, packet):
        self.in_batch = False
        logger.info(f'{self.name}: Batch ended on: {packet["submission-id"]}')
        json_log.info(self._make_json_log(
            packet, action='batch-end', batch=self.batch_id))

    # def on_test_case(self, packet, max_feedback=SubmissionTestCase._meta.get_field('feedback').max_length):
    #     logger.info('%s: %d test case(s) completed on: %s', self.name,
    #                 len(packet['cases']), packet['submission-id'])

    #     id = packet['submission-id']
    #     updates = packet['cases']
    #     max_position = max(map(itemgetter('position'), updates))

    #     if not Submission.objects.filter(id=id).update(current_testcase=max_position + 1):
    #         logger.warning('Unknown submission: %s', id)
    #         json_log.error(self._make_json_log(
    #             packet, action='test-case', info='unknown submission'))
    #         return

    #     bulk_test_case_updates = []
    #     for result in updates:
    #         test_case = SubmissionTestCase(
    #             submission_id=id, case=result['position'])
    #         status = result['status']
    #         if status & 4:
    #             test_case.status = 'TLE'
    #         elif status & 8:
    #             test_case.status = 'MLE'
    #         elif status & 64:
    #             test_case.status = 'OLE'
    #         elif status & 2:
    #             test_case.status = 'RTE'
    #         elif status & 16:
    #             test_case.status = 'IR'
    #         elif status & 1:
    #             test_case.status = 'WA'
    #         elif status & 32:
    #             test_case.status = 'SC'
    #         else:
    #             test_case.status = 'AC'
    #         test_case.time = result['time']
    #         test_case.memory = result['memory']
    #         test_case.points = result['points']
    #         test_case.total = result['total-points']
    #         test_case.batch = self.batch_id if self.in_batch else None
    #         test_case.feedback = (result.get('feedback') or '')[:max_feedback]
    #         test_case.extended_feedback = result.get('extended-feedback') or ''
    #         test_case.output = result['output']
    #         bulk_test_case_updates.append(test_case)

    #         json_log.info(self._make_json_log(
    #             packet, action='test-case', case=test_case.case, batch=test_case.batch,
    #             time=test_case.time, memory=test_case.memory, feedback=test_case.feedback,
    #             extended_feedback=test_case.extended_feedback, output=test_case.output,
    #             points=test_case.points, total=test_case.total, status=test_case.status,
    #         ))

    #     do_post = True

    #     if id in self.update_counter:
    #         cnt, reset = self.update_counter[id]
    #         cnt += 1
    #         if time.monotonic() - reset > UPDATE_RATE_TIME:
    #             del self.update_counter[id]
    #         else:
    #             self.update_counter[id] = (cnt, reset)
    #             if cnt > UPDATE_RATE_LIMIT:
    #                 do_post = False
    #     if id not in self.update_counter:
    #         self.update_counter[id] = (1, time.monotonic())

    #     if do_post:
    #         event.post('sub_%s' % Submission.get_id_secret(id), {
    #             'type': 'test-case',
    #             'id': max_position,
    #         })
    #         self._post_update_submission(id, state='test-case')

    #     SubmissionTestCase.objects.bulk_create(bulk_test_case_updates)

    async def on_malformed(self, packet):
        logger.error(f'{self.name}: Malformed packet: {packet}')
        json_log.exception(self._make_json_log(
            sub=self._working, info='malformed json packet'))

    async def on_ping_response(self, packet):
        end = datetime.datetime.now().timestamp()
        self._ping_average.append(end - packet['when'])
        self._time_delta.append((end + packet['when']) / 2 - packet['time'])
        self.latency = sum(self._ping_average) / len(self._ping_average)
        self.time_delta = sum(self._time_delta) / len(self._time_delta)
        self.load = packet['load']
        self._update_ping()

    def _free_self(self, packet):
        self.judges.on_judge_free(self, packet['submission-id'])

    async def _ping_thread(self):
        async def wait4stop():
            return await self._stop_ping.wait()
        try:
            while True:
                await self.ping()
                try:
                    await asyncio.wait_for(wait4stop(), timeout=10)
                    break
                except asyncio.exceptions.TimeoutError:
                    pass
                except:
                    traceback.print_exc()
        except Exception:
            logger.exception(f'Ping error in {self.name}')
            self.close()
            raise

    def _make_json_log(self, packet=None, sub=None, **kwargs):
        from bson import ObjectId
        class ObjectIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, ObjectId):
                    return str(obj)
                return super().default(obj)
        data = {
            'judge': self.name,
            'address': self.judge_address,
        }
        if sub is None and packet is not None:
            sub = packet.get('submission-id')
        if sub is not None:
            data['submission'] = sub
        data.update(kwargs)
        return json.dumps(data, cls=ObjectIDEncoder)

    # def _post_update_submission(self, id, state, done=False):
    #     if self._submission_cache_id == id:
    #         data = self._submission_cache
    #     else:
    #         self._submission_cache = data = Submission.objects.filter(id=id).values(
    #             'problem__is_public', 'contest_object__key',
    #             'user_id', 'problem_id', 'status', 'language__key',
    #         ).get()
    #         self._submission_cache_id = id

    #     if data['problem__is_public']:
    #         event.post('submissions', {
    #             'type': 'done-submission' if done else 'update-submission',
    #             'state': state, 'id': id,
    #             'contest': data['contest_object__key'],
    #             'user': data['user_id'], 'problem': data['problem_id'],
    #             'status': data['status'], 'language': data['language__key'],
    #         })
