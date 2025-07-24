import os
import subprocess
import tempfile
from pathlib import Path

from compiler.utils import is_file


def ir_to_x86(ir, file_path='.', file_name='output'):
    temp_file_name = None
    if not is_file(ir):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(ir)
            ir = temp_file.name
            temp_file_name = temp_file.name

    output_path = Path(file_path) / (file_name + '.s')
    command = ['clang', '-S', ir, '-o', output_path]
    subprocess.run(command, check=True)

    if not is_file(ir) and os.path.exists(temp_file_name):
        os.remove(temp_file_name)
    return output_path


def x86_to_exe(x86, file_path='.', file_name='output'):
    temp_file_name = None
    if not is_file(x86):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.s', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(x86)
            x86 = temp_file.name
            temp_file_name = temp_file.name

    output_path = Path(file_path) / (file_name + '.exe')
    command = ['clang', x86, '-o', output_path]
    subprocess.run(command, check=True)

    if not is_file(x86) and os.path.exists(temp_file_name):
        os.remove(temp_file_name)
    return output_path
