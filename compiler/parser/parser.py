from lark import Lark

from compiler.tree import ASTTransformer


class Parser:
    def __init__(self, file_path='compiler/parser/syntax.lark'):
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

    @property
    def table(self):
        inner_parser = self.parser.parser.parser
        inner_table = getattr(inner_parser, '_parse_table', None)
        return inner_table
