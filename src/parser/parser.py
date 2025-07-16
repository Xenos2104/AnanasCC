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

        transformer = ASTTransformer()
        tree = transformer.transform(tree)
        return tree


if __name__ == "__main__":
    from src.lexer.lexer import Lexer

    with open('test.c', encoding='utf-8') as f:
        code = f.read()

    lexer = Lexer('../lexer/lexicon.lark')
    tokens = lexer.lex(code)

    parser = Parser('syntax.lark')
    tree = parser.parse(tokens)

    print(tree.pretty())
