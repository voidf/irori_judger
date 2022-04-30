# logger = logging.getLogger('judge.bridge')
import asyncio
from collections import namedtuple
import datetime
from models.submission import Submission
from loguru import logger
from operator import attrgetter
try:
    from llist import dllist
except ImportError:
    from pyllist import dllist

UPDATE_RATE_LIMIT = 5
UPDATE_RATE_TIME = 0.5

PriorityMarker = namedtuple('PriorityMarker', 'priority')

class JudgeList(object):
    """这个应该是个单例，负责管理所有的评测机连接"""
    priorities = 4

    def __init__(self):
        self.queue = dllist()
        self.priority = [self.queue.append(
            PriorityMarker(i)) for i in range(self.priorities)]
        self.judges = set()
        self.node_map = {}
        self.submission_map = {}
        # self.lock = asyncio.Lock()

    @logger.catch
    def _handle_free_judge(self, judge):
        # with self.lock:
        node = self.queue.first
        while node:
            if not isinstance(node.value, PriorityMarker):
                id, problem, language, source, judge_id = node.value
                if judge.can_judge(problem, language, judge_id):
                    self.submission_map[id] = judge
                    try:
                        asyncio.create_task(judge.submit(id, problem, language, source))
                    except Exception:
                        logger.exception(
                            f'Failed to dispatch {id} ({problem}, {language}) to {judge.name}')
                        self.judges.remove(judge)
                        return
                    logger.info(
                        f'Dispatched queued submission {id}: {judge.name}')
                    self.queue.remove(node)
                    del self.node_map[id]
                    break
            node = node.next

    def register(self, judge):
        # with self.lock:
        # Disconnect all judges with the same name, see <https://github.com/DMOJ/online-judge/issues/828>
        self.disconnect(judge, force=True)
        self.judges.add(judge)
        self._handle_free_judge(judge)

    def disconnect(self, judge_id, force=False):
        # with self.lock:
        for judge in self.judges:
            if judge.name == judge_id:
                judge.disconnect(force=force)

    def update_problems(self, judge):
        # with self.lock:
        self._handle_free_judge(judge)

    def remove(self, judge):
        # with self.lock:
        sub = judge.get_current_submission()
        if sub is not None:
            try:
                del self.submission_map[sub]
            except KeyError:
                pass
        self.judges.discard(judge)

    def __iter__(self):
        return iter(self.judges)

    def on_judge_free(self, judge, submission):
        logger.info(
            f'Judge available after grading {submission}: {judge.name}')
        # with self.lock:
        del self.submission_map[submission]
        judge._working = False
        self._handle_free_judge(judge)

    def abort(self, submission):
        logger.info(f'Abort request: {submission}')
        # with self.lock:
        try:
            self.submission_map[submission].abort()
            return True
        except KeyError:
            try:
                node = self.node_map[submission]
            except KeyError:
                pass
            else:
                self.queue.remove(node)
                del self.node_map[submission]
            return False

    def check_priority(self, priority):
        return 0 <= priority < self.priorities

    async def gen_judge(self, problem, language, source, judge_id, priority):
        sid = Submission(
            # problem=problem,
            language=language,
            date=datetime.datetime.now()
        ).save().pk
        await self.judge(sid, problem, language, source, judge_id, priority)

    async def judge(self, id, problem, language, source, judge_id, priority):
        """应该在外部先创建好了对应的Submission数据库文档后再调用"""
        # with self.lock:
        if id in self.submission_map or id in self.node_map:
            # Already judging, don't queue again. This can happen during batch rejudges, rejudges should be
            # idempotent.
            return

        candidates = [
            judge for judge in self.judges if not judge.working and judge.can_judge(problem, language, judge_id)
        ]
        if judge_id:
            logger.info(
                f'Specified judge {judge_id} is{" " if candidates else " not "}available')
        else:
            logger.info(f'Free judges: {len(candidates)}')
        if candidates:
            # Schedule the submission on the judge reporting least load.
            judge = min(candidates, key=attrgetter('load'))
            logger.info(f'Dispatched submission {id} to: {judge.name}')
            self.submission_map[id] = judge
            try:
                await judge.submit(id, problem, language, source)
            except Exception:
                logger.exception(
                    f'Failed to dispatch {id} ({problem}, {language}) to {judge.name}')
                self.judges.discard(judge)
                return self.judge(id, problem, language, source, judge_id, priority)
        else:
            self.node_map[id] = self.queue.insert(
                (id, problem, language, source, judge_id),
                self.priority[priority],
            )
            logger.info(f'Queued submission: {id}')

judge_list: JudgeList = JudgeList()
