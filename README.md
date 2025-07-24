# AnanasCC 🍍 C编译器

<div style="text-align: center;">
  <img src="https://img.shields.io/badge/language-Python-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/compiler-C_to_X86-orange.svg" alt="Compiler">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</div>

## 项目简介

广西大学2025编译原理课程设计。

AnanasCC（Ananas C Compiler）是一个用Python实现的C语言到X86的编译器。

该编译器支持C语言的主要特性和部分C++特性，能够将C代码编译为X86汇编代码，并可进一步生成可执行文件。

## 编译流程

- **词法分析**：基于Lark解析器，将C源码转换为标记流
- **语法分析**：基于Lark解析器，构建抽象语法树（AST）
- **语义分析**：遍历AST，进行类型检查和符号表管理
- **中间代码**：遍历AST，为节点生成LLVM IR
- **代码优化**：支持多级优化
- **目标代码**：将IR转换为X86汇编代码（可进一步得到exe）

各阶段均分离实现，通过AST交互。

## 支持的C/C++特性

- 基本数据类型（int, float, char, bool等）
- 变量声明与初始化
- 控制流语句（if-else, for, while, break, continue等）
- 表达式计算（不包括位运算）
- 函数定义与调用
- 指针与数组
- 结构体与共用体
- 枚举

## 项目结构

```
AnanasCC/
├── compiler/               # 核心代码
│   ├── error/              # 错误处理模块
│   │   └── error.py        # 各类编译错误
│   ├── lexer/              # 词法分析模块
│   │   ├── lexer.py        # 词法分析器实现
│   │   └── lexicon.lark    # 词法规则定义
│   ├── parser/             # 语法分析模块
│   │   ├── parser.py       # 语法分析器实现
│   │   └── syntax.lark     # 语法规则定义
│   ├── semantic/           # 语义分析模块
│   │   ├── analyzer.py     # 语义分析器实现
│   │   ├── symbol.py       # 符号表管理
│   │   └── type.py         # 类型系统
│   ├── ir/                 # 中间代码模块
│   │   ├── generator.py    # IR生成器
│   │   └── optimizer.py    # IR优化器
│   ├── tree/               # AST
│   │   ├── transformer.py  # CST到AST的转换
│   │   └── tree.py         # AST节点定义
│   ├── x86/                # 目标代码模块
│   │   └── x86.py          # IR到X86的转换
│   ├── compiler.py         # 编译器主类
│   ├── __main__.py         # 命令行接口
│   └── utils.py            # 工具函数
├── tests/                  # 测试用例
│   ├── test.c              # 综合测试用例
│   ├── task1.c             # 任务1测试用例
│   ├── task2.c             # 任务2测试用例
│   └── test.py             # 测试脚本
├── output/                 # 输出目录
│   └── output.s            # 生成的汇编代码
├── temp/                   # 中间文件目录
│   ├── 01 tokens.txt       # 单词表
│   ├── 02 action_table.txt # ACTION表
│   ├── 02 goto_table.txt   # GOTO表
│   ├── 03 ast.txt          # 抽象语法树
│   ├── 03 cst.txt          # 具体语法树
│   ├── 04 opt_ir.txt       # 优化IR
│   └── 04 org_ir.txt       # 原始IR
├── main.c                  # Hello World
├── main.py                 # 主程序入口
└── requirements.txt        # 项目依赖
```

## 安装与使用

### 使用可执行文件

直接下载并使用`AnanasCC.exe`，需要安装LLVM（Clang）

```bash
# 编译
AnanasCC.exe your_file.c

# 编译并执行
AnanasCC.exe your_file.c -e 
```

#### 命令行参数

```
usage: AnanasCC [-h] [-e] input_file

一个简单的C编译器。

positional arguments:
  input_file         要编译的C源文件路径

optional arguments:
  -h, --help         显示帮助信息并退出
  -e, --execute      编译完成后立即执行程序
```

### 从源码运行

#### 开发环境

- Python 3.12
- Lark 1.2.2
- LLVM

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 使用方法

1. 编写C源代码（如main.c）
2. 运行编译器

```bash
# 使用主程序
python main.py

# 使用模块
python -m compiler your_file.c -e
```

默认情况下，编译器会编译`main.c`文件，并在`output`目录下生成汇编代码和可执行文件。

## 示例

### 简单的Hello World程序

```c
int main()
{
    printf("Hello, World!\n");
    return 0;
}
```

### 更复杂的示例

```c
int add(int a, int *b)
{
    return a + *b;
}

struct Apple
{
    char color;
    Apple* size;
    char* name;
};

enum Bool
{
    TRUE = 0,
    FALSE
};

bool test()
{
    int a = 10, d = 3;
    int* b = &a;
    *b = 20;
    int c;
    
    if (a > 20)
        c = 3;
    else if (a == 10)
        c = 2;
    else
        c = 1;

    Apple apple = {'c', nullptr, "菠萝"};
    apple.name = "苹果";
    
    return c == add(a, b);
}

int main(void)
{
    Bool a;
    if (test())
        a = 1;
    else
        a = 0;
    return a;
}
```

## 开发与扩展

### 添加新的语言特性

要添加新特性，需要调整以下组件。

1. 在`lexer/lexicon.lark`中添加新的词法规则
2. 在`parser/syntax.lark`中添加新的语法规则
3. 在`tree/transformer.py`中添加相应的AST节点转换逻辑
4. 在`semantic/analyzer.py`中添加语义分析规则
5. 在`ir/generator.py`中实现中间代码生成

### 打包为可执行文件

AnanasCC已被打包为独立的可执行文件，使用PyInstaller实现。

如需自行打包，可以使用以下命令。

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包为单个可执行文件
pyinstaller --onefile --name AnanasCC compiler/__main__.py
```

## 当前限制

- 不支持预处理器指令
- 不支持位运算
- 不支持可变参数函数
- 不支持强制类型转换
- 不支持函数指针

## 许可证

本项目采用MIT许可证。详情请参阅[LICENSE](LICENSE)文件。
