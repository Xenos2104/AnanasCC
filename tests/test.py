from compiler.error import CompileError
from compiler.ir import IRGenerator
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import Analyzer

if __name__ == '__main__':
    show_code, show_tokens, show_tree, show_ir = 1, 1, 1, 1

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
        print(' C  CODE '.center(40, '='))
        print(code)
    if show_tokens:
        print('  TOKEN  '.center(40, '='))
        list(map(lambda token: print(f'({token.type}, {token.value})'), tokens))
    if show_tree:
        print('   AST   '.center(40, '='))
        print(tree.pretty())
    if show_ir:
        print(' LLVM IR '.center(40, '='))
        print(ir)
