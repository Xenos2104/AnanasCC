from lark import Lark


class Lexer:
    def __init__(self, file_path='compiler/lexer/lexicon.lark'):
        with open(file_path, encoding='utf-8') as f:
            self.lexicon = f.read()
        self.lexer = Lark(self.lexicon, lexer='basic')

    def lex(self, code):
        tokens = list(self.lexer.lex(code))
        return tokens


if __name__ == "__main__":
    with open('test.c', encoding='utf-8') as f:
        code = f.read()

    lexer = Lexer('lexicon.lark')
    tokens = lexer.lex(code)

    for token in tokens:
        print(f'({token.type}, {token.value})')
