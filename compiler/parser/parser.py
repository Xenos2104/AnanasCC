from pathlib import Path

from lark import Lark, UnexpectedToken
from tabulate import tabulate

from compiler.error import SyntaxError
from compiler.tree import ASTTransformer
from compiler.utils import read_file, write_file


class Parser:
    def __init__(self, file_path='syntax.lark'):
        self.file_path = Path(__file__).parent / file_path
        self.syntax = read_file(self.file_path)
        self.parser = Lark(self.syntax, parser='lalr', propagate_positions=True)
        self.cst = None
        self.ast = None

    def parse(self, tokens):
        ip = self.parser.parse_interactive()

        try:
            for token in tokens:
                ip.feed_token(token)
            self.cst = ip.feed_eof(tokens[-1])
        except UnexpectedToken as e:
            raise SyntaxError('无法识别的单词', e.line, e.column)

        transformer = ASTTransformer()
        self.ast = transformer.transform(self.cst)
        return self.ast

    @property
    def table(self):
        inner_parser = self.parser.parser.parser
        inner_table = getattr(inner_parser, '_parse_table', None)
        return inner_table

    @staticmethod
    def tabular(table):
        action_rows = []
        for state, actions in table.states.items():
            for token, (action, arg) in actions.items():
                if getattr(action, '__name__', str(action)) == "Shift":
                    action_rows.append([state, token, "SHIFT", arg])
                elif getattr(action, '__name__', str(action)) == "Reduce":
                    action_rows.append([state, token, "REDUCE", getattr(arg, 'origin', arg)])
                else:
                    action_rows.append([state, token, str(action), arg])
        action_table = tabulate(action_rows,
                                headers=["State", "Token", "Action", "Arg"],
                                tablefmt="simple_grid",
                                numalign="center",
                                stralign="center")
        goto_rows = []
        for state, actions in table.states.items():
            for token, (action, arg) in actions.items():
                if getattr(action, '__name__', str(action)) == "Shift" and not token.islower():
                    goto_rows.append([state, token, "GOTO", arg])
        goto_table = tabulate(goto_rows,
                              headers=["State", "Token", "Action", "Arg"],
                              tablefmt="simple_grid",
                              numalign="center",
                              stralign="center")
        return action_table, goto_table

    def save(self, file_path=''):
        action_table, goto_table = self.tabular(self.table)
        write_file(action_table, Path(file_path) / '02 action_table.txt')
        write_file(goto_table, Path(file_path) / '02 goto_table.txt')

        write_file(self.cst.pretty(), Path(file_path) / '03 cst.txt')
        write_file(self.ast.pretty(), Path(file_path) / '03 ast.txt')
