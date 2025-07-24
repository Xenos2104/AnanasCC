from pathlib import Path

from lark import Lark, UnexpectedCharacters
from tabulate import tabulate

from compiler.error import LexicalError
from compiler.utils import read_file, write_file


class Lexer:
    def __init__(self, file_path='lexicon.lark'):
        self.file_path = Path(__file__).parent / file_path
        self.lexicon = read_file(self.file_path)
        self.lexer = Lark(self.lexicon, lexer='basic')
        self.tokens = None

    def lex(self, code):
        try:
            self.tokens = list(self.lexer.lex(code))
        except UnexpectedCharacters as e:
            raise LexicalError('无法识别的字符', e.line, e.column)
        return self.tokens

    @staticmethod
    def tabular(tokens):
        rows = []
        for token in tokens:
            rows.append([token.type, token.value, token.line, token.column])
        table = tabulate(rows, ["Type", "Value", "Line", "Column"], "simple_grid", numalign="center", stralign="center")
        return table

    def save(self, file_path=''):
        write_file(self.tabular(self.tokens), Path(file_path) / '01 tokens.txt')
