class Type:
    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __repr__(self):
        return self.__class__.__name__

    def __hash__(self):
        return hash(repr(self))


class BasicType(Type):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return super().__eq__(other) and self.name == other.name

    def __repr__(self):
        return self.name


class PointerType(Type):
    def __init__(self, type):
        self.type = type

    def __eq__(self, other):
        return super().__eq__(other) and self.type == other.type

    def __repr__(self):
        return str(self.type) + '*'


class ArrayType(Type):
    def __init__(self, type, size=None):
        self.type = type
        self.size = size

    def __eq__(self, other):
        return super().__eq__(other) and self.type == other.type

    def __repr__(self):
        type = str(self.type)
        size = str(self.size) if self.size else ''
        return type + '[' + size + ']'


class FunctionType(Type):
    def __init__(self, type, params):
        self.type = type
        self.params = params

    def __eq__(self, other):
        return (super().__eq__(other) and
                self.type == other.type and
                self.params == other.params)

    def __repr__(self):
        type = str(self.type)
        params = ', '.join(map(str, self.params))
        return type + '(' + params + ')'


class CompoundType(Type):
    def __init__(self, name, members, union=False):
        self.name = name
        self.members = members
        self.union = union

    def __eq__(self, other):
        return (super().__eq__(other) and
                self.name == other.name and
                self.union == other.union)

    def __repr__(self):
        return self.name


class EnumType(Type):
    def __init__(self, name, enumerators):
        self.name = name
        self.enumerators = enumerators

    def __eq__(self, other):
        return super().__eq__(other) and self.name == other.name

    def __repr__(self):
        return self.name


VOID = BasicType('void')
INT = BasicType('int')
FLOAT = BasicType('float')
CHAR = BasicType('char')
BOOL = BasicType('bool')
NULL = BasicType('nullptr')
