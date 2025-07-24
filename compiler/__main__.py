import argparse
import sys
from pathlib import Path

from compiler.error import CompileError
from compiler.compiler import Compiler


def main():
    parser = argparse.ArgumentParser(prog="AnanasCC", description="一个简单的C编译器。")
    parser.add_argument("input_file", help="要编译的C源文件路径。")
    parser.add_argument("-e", "--execute", action="store_true", help="编译完成后立即执行程序。")

    args = parser.parse_args()

    # 验证输入文件是否存在
    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"错误: 输入文件 '{input_path}' 不存在或不是一个文件。", file=sys.stderr)
        sys.exit(1)

    # 确定工作目录和文件路径
    work_dir = input_path.parent.resolve()
    file_path = str(input_path.resolve())

    # 运行编译器
    try:
        print(f"工作目录: {work_dir}")
        print(f"开始编译: {file_path}")
        compiler = Compiler(work_dir=str(work_dir))
        compiler.compile(file_path, execute=args.execute)
        print("\n编译成功！")

    except CompileError as e:
        print(f"\n编译失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
