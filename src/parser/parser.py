from lark import Lark

from src.tree import ASTTransformer


class Parser:
    def __init__(self, file_path='src/parser/syntax.lark'):
        with open(file_path, encoding='utf-8') as f:
            self.syntax = f.read()
        self.parser = Lark(self.syntax, parser='lalr', propagate_positions=True)

    def parse(self, tokens):
        ip = self.parser.parse_interactive()
        for token in tokens:
            ip.feed_token(token)
        tree = ip.feed_eof(tokens[-1])
        print(tree.pretty())

        transformer = ASTTransformer()
        tree = transformer.transform(tree)
        return tree


if __name__ == "__main__":
    from src.lexer.lexer import Lexer
    from src.error import CompileError
    from src.semantic.analyzer import Analyzer

    with open('test.c', encoding='utf-8') as f:
        code = f.read()

    lexer = Lexer('../lexer/lexicon.lark')
    tokens = lexer.lex(code)

    parser = Parser('syntax.lark')
    tree = parser.parse(tokens)
    print(tree.pretty())

    try:
        from src.semantic.analyzer import Analyzer

        analyzer = Analyzer()
        analyzer.analyze(tree)
        print('语义分析没发现错误（至少目前没有）')
        print(analyzer.table)
    except CompileError as e:
        print(e)
