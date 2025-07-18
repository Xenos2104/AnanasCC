from compiler.error import CompileError
from compiler.ir import IRGenerator
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import Analyzer

if __name__ == '__main__':
    show_code = 0
    show_tokens = 0
    show_tree = 1
    show_ir = 0

    with open('test.c', encoding='utf-8') as f:
        code = f.read()

    try:
        lexer = Lexer('../compiler/lexer/lexicon.lark')
        tokens = lexer.lex(code)

        parser = Parser('../compiler/parser/syntax.lark')
        tree = parser.parse(tokens)

        analyzer = Analyzer()
        tree = analyzer.analyze(tree)

        generator = IRGenerator()
        ir = generator.generate(tree)

    except CompileError as e:
        print(e)

    if show_code:
        print('===============  C代码  ===============')
        print(code)
    if show_tokens:
        print('===============  单 词  ===============')
        list(map(lambda token: print(f'({token.type}, {token.value})'), tokens))
    if show_tree:
        print('===============  语法树  ===============')
        print(tree.pretty())
    if show_ir:
        print('=============== 中间代码 ===============')
        print(ir)
