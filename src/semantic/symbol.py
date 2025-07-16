from enum import Enum, auto


class Symbol:
    def __init__(self, type, name, kind, node=None, defined=True):
        self.type = type
        self.name = name
        self.kind = kind
        self.node = node
        self.defined = defined

    def __repr__(self):
        return f'Symbol({self.type}, {self.name}, {self.kind}, {self.node})'


class SymbolKind(Enum):
    TYPE = auto()
    FUNC = auto()
    VAR = auto()
    CONST = auto()


class SymbolTable:
    def __init__(self):
        self.stack = []
        self.enter_scope()

    def enter_scope(self):
        self.stack.append({})

    def leave_scope(self):
        if len(self.stack) > 1:
            self.stack.pop()

    def define(self, symbol):
        scope = self.stack[-1]
        if symbol.name in scope:
            return False
        else:
            scope[symbol.name] = symbol
            return True

    def lookup(self, name):
        for scope in reversed(self.stack):
            if name in scope:
                return scope[name]
        return None
