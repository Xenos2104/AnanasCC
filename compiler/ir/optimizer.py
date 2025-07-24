from pathlib import Path

from llvmlite import binding

from compiler.utils import write_file


class Optimizer:
    def __init__(self, opt_level=2, size_level=0):
        self.opt_level = opt_level
        self.size_level = size_level

        self.pmb = binding.PassManagerBuilder()
        self.pmb.opt_level = self.opt_level
        self.pmb.size_level = self.size_level

        self.ir = None

    def optimize(self, ir):
        module = binding.parse_assembly(str(ir))
        pm = binding.ModulePassManager()
        self.pmb.populate(pm)

        pm.add_dead_code_elimination_pass()
        pm.add_function_inlining_pass(self.opt_level)

        pm.run(module)
        self.ir = str(module)
        return self.ir

    def save(self, file_path=''):
        write_file(self.ir, Path(file_path) / '04 opt_ir.txt')
