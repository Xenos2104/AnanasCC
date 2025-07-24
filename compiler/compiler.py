import os
import subprocess

from compiler.error import CompileError
from compiler.ir import Generator
from compiler.ir import Optimizer
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import Analyzer
from compiler.utils import read_file
from compiler.x86 import ir_to_x86, x86_to_exe


class Compiler:
    def __init__(self, work_dir):
        os.makedirs(work_dir, exist_ok=True)
        self.work_dir = work_dir

        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = Analyzer()
        self.generator = Generator()
        self.optimizer = Optimizer()

    def compile(self, file_path, execute=False):
        code = read_file(file_path)

        try:
            tokens = self.lexer.lex(code)
            tree = self.parser.parse(tokens)
            tree = self.analyzer.analyze(tree)
        except CompileError as e:
            print(e)

        ir = self.generator.generate(tree)
        ir = self.optimizer.optimize(ir)

        x86 = ir_to_x86(ir, self.work_dir)
        exe = x86_to_exe(x86, self.work_dir)

        if execute:
            result = subprocess.run(exe)
            exit_code = result.returncode if result.returncode <= (2**31 - 1) else result.returncode - 2**32
            print(f'\n进程已结束，退出代码为 {exit_code}')

    def save(self, file_path=''):
        self.lexer.save(file_path)
        self.parser.save(file_path)
        self.generator.save(file_path)
        self.optimizer.save(file_path)
