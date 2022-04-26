import tempfile
from dmoj.cptbox.filesystem_policies import RecursiveDir
from dmoj.result import CheckerResult
import os
import shlex
import subprocess

from dmoj.contrib import contrib_modules
from dmoj.error import InternalError
from dmoj.graders.standard import StandardGrader
from dmoj.judgeenv import env, get_problem_root
from dmoj.utils.helper_files import mktemp
from dmoj.utils.unicode import utf8bytes, utf8text
from dmoj.executors.CPP20 import Executor

def checker(
    process_output,
    judge_output,
    judge_input,
    problem_id,
    files,
    time_limit=env['generator_time_limit'],
    memory_limit=env['generator_memory_limit'],
    feedback=True,
    type='default',
    args_format_string=None,
    point_value=None,
    **kwargs
) -> CheckerResult:
    absfp = os.path.join(get_problem_root(problem_id), files) # spj可执行文件绝对路径
    with open(absfp, 'rb') as f:
        sources = f.read()

    if type not in contrib_modules:
        raise InternalError('%s is not a valid contrib module' % type)

    args_format_string = args_format_string or contrib_modules[type].ContribModule.get_checker_args_format_string()

    with mktemp(judge_input) as input_file, mktemp(process_output) as answer_file, mktemp(judge_output) as output_file: # CSUOJ与dmoj的默认checker后两个文件顺序相反
        class CSUOJSPJ_Executor(Executor):
            ext = files.split('.')[-1]
            command = './'+files
            def compile(self) -> str:
                self._executable = self.get_compiled_file() + '.elf'
                # shutil.copy2(absfp, self._executable)
                with open(self._executable, 'wb') as f:
                    f.write(sources)
                os.chmod(self._executable, 0o744)
                return self._executable
            def get_binary_cache_key(self) -> bytes:
                key_components = (
                    [self.problem, 'CSUOJ_SPJ', self.get_march_flag()] + self.get_defines() + self.get_flags() + self.get_ldflags()
                )
                return utf8bytes(''.join(key_components)) + b''.join(self.source_dict.values())
            def get_cmdline(self, **kwargs):
                return [self._executable]
            def get_executable(self) -> str:
                return self._executable
        executor = CSUOJSPJ_Executor(
            '_aux_file',
            sources,
            cached=True,
            fs=CSUOJSPJ_Executor.fs + [RecursiveDir(tempfile.gettempdir())] # 开权限
        )
        checker_args = shlex.split(
            args_format_string.format(
                input_file=shlex.quote(input_file.name),
                output_file=shlex.quote(output_file.name),
                answer_file=shlex.quote(answer_file.name),
            )
        )
        process = executor.launch(
            *checker_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, memory=memory_limit, time=time_limit
        )

        proc_output, error = process.communicate()
        proc_output = utf8text(proc_output)

        return contrib_modules[type].ContribModule.parse_return_code(
            process,
            executor,
            point_value,
            time_limit,
            memory_limit,
            feedback=utf8text(proc_output) if feedback else '',
            name='checker',
            stderr=error,
        )


class Grader(StandardGrader):
    def check_result(self, case, result):
        ck = case.checker()
        fp = ck.keywords['files'][0]
        if not result.result_flag:
            try:
                check = checker(
                    result.proc_output,
                    case.output_data(),
                    files=fp,
                    submission_source=self.source,
                    judge_input=case.input_data(),
                    point_value=case.points,
                    case_position=case.position,
                    batch=case.batch,
                    submission_language=self.language,
                    binary_data=case.has_binary_data,
                    execution_time=result.execution_time,
                    problem_id=self.problem.id,
                    result=result,
                )
            except UnicodeDecodeError:
                return CheckerResult(False, 0, feedback='invalid unicode')
        else:
            check = False
        return check