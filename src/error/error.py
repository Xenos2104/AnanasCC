class CompileError(Exception):
    def __init__(self, msg, line, column):
        super().__init__(msg)
        self.msg = msg
        self.line = line
        self.column = column

    def __str__(self):
        return f'{self.__class__.__name__}({self.line}, {self.column}): {self.msg}'


class LexicalError(CompileError):
    pass


class SyntaxError(CompileError):
    pass


class SemanticError(CompileError):
    pass


if __name__ == '__main__':
    try:
        raise SemanticError('这是一个语义错误', 11, 3)
    except CompileError as e:
        print(e)
