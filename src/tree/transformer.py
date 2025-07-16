from types import SimpleNamespace as Meta

from lark import Transformer, Token
from lark import v_args

from .tree import *


@v_args(inline=True, meta=True)
class ASTTransformer(Transformer):
    @staticmethod
    def program(meta, *args):
        args = [i for i in args if i is not None]
        decl = ExternalDeclaration(args, meta)
        return Program(decl, meta)

    @staticmethod
    def unit(_, child):
        return child

    @staticmethod
    def definition(_, child):
        return child

    @staticmethod
    def declaration(_, child):
        return child

    @staticmethod
    def specifier(meta, type):
        return Specifier(type.value, meta)

    @staticmethod
    def declarator(meta, *args):
        name, pointer = None, False
        if len(args) == 1:
            name = args[0]
        else:
            name = args[1]
            pointer = True
        return Declarator(name, pointer, meta=meta)

    @staticmethod
    def initializer(meta, *args):
        if len(args) == 1:
            return args[0]
        else:
            inits = [i for i in args if not isinstance(i, Token)]
            return Initializer(inits, meta)

    @staticmethod
    def array_suffix(meta, *args):
        size = None
        if len(args) == 3:
            size = args[1]
        return ArraySuffix(size, meta)

    @staticmethod
    def param_suffix(meta, *args):
        params = []
        if len(args) == 3:
            if isinstance(args[1], list):
                params = args[1]
            else:
                params = ['void']
        return ParamSuffix(params, meta)


    @staticmethod
    def param_list(_, *args):
        return list(args[::2])

    @staticmethod
    def param_item(meta, spec, decl):
        return Parameter(spec, decl, meta)

    @staticmethod
    def func_def(meta, spec, decl, suffix, body):
        decl.suffix.append(suffix)
        decl.update()
        return FunctionDefinition(spec, decl, body, meta)


    @staticmethod
    def comp_def(meta, spec, decl, _, members, __, ___):
        spec = Specifier(spec, meta)
        return CompoundDefinition(spec, decl, members, meta)

    @staticmethod
    def comp_list(_, *args):
        return list(args)

    @staticmethod
    def comp_item(meta, spec, decls, _):
        return Member(spec, decls, meta)

    @staticmethod
    def member_list(_, *args):
        return list(args[::2])

    @staticmethod
    def member_item(_, decl, *suffix):
        decl.suffix.extend(suffix)
        decl.update()
        return decl

    @staticmethod
    def enum_def(meta, _, name, __, enumerators, ___, ____):
        return EnumDefinition(name, enumerators, meta)

    @staticmethod
    def enum_list(_, *args):
        return list(args[::2])

    @staticmethod
    def enum_item(meta, name, _=None, value=None):
        return Enumerator(name, value, meta)

    @staticmethod
    def func_decl(meta, spec, decls, _):
        return FunctionDeclaration(spec, decls, meta)

    @staticmethod
    def func_list(_, *args):
        return list(args[::2])

    @staticmethod
    def func_item(_, decl, suffix):
        decl.suffix.append(suffix)
        decl.update()
        return decl

    @staticmethod
    def var_decl(meta, spec, decls, _):
        return VariableDeclaration(spec, decls, meta)

    @staticmethod
    def var_list(_, *args):
        return list(args[::2])

    @staticmethod
    def var_item(_, decl, __=None, init=None):
        if init is not None:
            decl.init = init
            decl.update()
        return decl

    @staticmethod
    def arr_decl(meta, spec, decls, _):
        return ArrayDeclaration(spec, decls, meta)

    @staticmethod
    def arr_list(_, *args):
        return list(args[::2])

    @staticmethod
    def arr_item(_, *args):
        decl = args[0]
        i = 1
        while i < len(args) and isinstance(args[i], ArraySuffix):
            decl.suffix.append(args[i])
            i += 1
        if i < len(args):
            decl.init = args[i + 1]
        decl.update()
        return decl

    @staticmethod
    def statement(_, child):
        return child

    @staticmethod
    def comp_stmt(meta, _, *args):
        stmts = list(args[:-1])
        return Statement(stmts, meta)

    @staticmethod
    def expr_stmt(meta, *args):
        if len(args) == 2:
            expr = args[0]
            return ExpressionStatement(expr, meta)
        return None

    @staticmethod
    def select_stmt(meta, _, __, cond, ___, then, ____=None, orelse=None):
        return IfStatement(cond, then, orelse, meta)

    @staticmethod
    def iter_stmt(meta, *args):
        if args[0].type == 'WHILE':
            cond = args[2]
            body = args[4]
            return WhileStatement(cond, body, meta)
        else:
            init = args[2]
            body = args[-1]
            try:
                semi = args.index(next(i for i in args if isinstance(i, Token) and i.type == 'SEMICOLON'))
                cond = args[3] if semi > 3 else None
                post = args[semi + 1] if semi + 1 < len(args) - 2 else None
            except StopIteration:
                cond, post = None, None
            return ForStatement(init, cond, post, body, meta)

    @staticmethod
    def jump_stmt(meta, *args):
        if args[0].type == 'CONTINUE':
            return ContinueStatement(meta)

        elif args[0].type == 'BREAK':
            return BreakStatement(meta)
        else:
            expr = args[1] if len(args) == 3 else None
            return ReturnStatement(expr, meta=meta)

    @staticmethod
    def expression(meta, *args):
        exprs = list(args[::2])
        return Expression(exprs, meta)

    @staticmethod
    def assign_expr(meta, *args):
        if len(args) == 1:
            return args[0]
        else:
            op, left, right = args[1].value, args[0], args[2]
            return AssignOp(op, left, right, meta)

    @staticmethod
    def assign(_, child):
        return child

    @staticmethod
    def process_binary_op(meta, *args):
        left = args[0]
        i = 1
        while i < len(args):
            op, right = args[i], args[i + 1]
            left = BinaryOp(op.value, left, right, meta)
            i += 2
        return left

    def lor_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    def land_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    def equal_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    def rel_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    def add_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    def mul_expr(self, meta, *args):
        return self.process_binary_op(meta, *args)

    @staticmethod
    def unary_expr(meta, *args):
        if len(args) == 1:
            return args[0]
        else:
            op = args[0].value
            operand = args[1]
            return UnaryOp(op, operand, meta)

    @staticmethod
    def postfix_expr(meta, *args):
        node = args[0]
        i = 1
        while i < len(args):
            op = args[i]
            if isinstance(op, list) or op is None:
                node = FunctionCall(node, op or [], meta)
                i += 1
            elif op.type == 'LBRACK':
                node = ArrayAccess(node, args[i + 1], meta)
                i += 2
            elif op.type in ('DOT', 'ARROW'):
                arrow = (op.type == 'ARROW')
                member = args[i + 1]
                node = MemberAccess(node, member, arrow, meta)
                i += 2
            elif op.type in ('INCREMENT', 'DECREMENT'):
                node = PostfixOp(op.value, node, meta)
                i += 1
            else:
                i += 1
        return node

    @staticmethod
    def argument(_, *args):
        return list(args[::2])

    @staticmethod
    def const_expr(_, child):
        return child

    @staticmethod
    def primary_expr(_, *args):
        if len(args) == 1:
            return args[0]
        else:
            return args[1]

    @staticmethod
    def const(_, child):
        return child

    @staticmethod
    def INTEGER(token):
        meta = Meta(line=token.line, column=token.column)
        return Integer(token.value, meta)

    @staticmethod
    def DECIMAL(token):
        meta = Meta(line=token.line, column=token.column)
        return Decimal(token.value, meta)

    @staticmethod
    def CHARACTER(token):
        meta = Meta(line=token.line, column=token.column)
        return Character(token.value, meta)

    @staticmethod
    def STRING(token):
        meta = Meta(line=token.line, column=token.column)
        return String(token.value, meta)

    @staticmethod
    def TRUE(token):
        meta = Meta(line=token.line, column=token.column)
        return Bool(token.value, meta)

    @staticmethod
    def FALSE(token):
        meta = Meta(line=token.line, column=token.column)
        return Bool(token.value, meta)

    @staticmethod
    def NULLPTR(token):
        meta = Meta(line=token.line, column=token.column)
        return NullPtr(meta)

    @staticmethod
    def IDENT(token):
        meta = Meta(line=token.line, column=token.column)
        return Identifier(token.value, meta)

    @staticmethod
    def TYPE(token):
        meta = Meta(line=token.line, column=token.column)
        return Identifier(token.value, meta)

    @staticmethod
    def IMM(token):
        meta = Meta(line=token.line, column=token.column)
        return Identifier(token.value, meta)
