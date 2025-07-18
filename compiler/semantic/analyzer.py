from lark.visitors import Interpreter

from compiler.error import SemanticError
from compiler.tree import *
from .symbol import Symbol, SymbolKind, SymbolTable
from .type import *


class Analyzer(Interpreter):
    def __init__(self):
        super().__init__()
        self.table = SymbolTable()
        self.curr_func = None
        self.loop_depth = 0

        for name, type in [('void', VOID), ('int', INT), ('float', FLOAT), ('char', CHAR), ('bool', BOOL)]:
            symbol = Symbol(type, name, SymbolKind.TYPE)
            self.table.define(symbol)

    # ===============  基础方法  ===============

    @staticmethod
    def raise_error(msg, node):
        raise SemanticError(msg, node.line, node.column)

    def analyze(self, tree):
        self.visit(tree)
        return tree

    # ===============  辅助方法  ===============

    def parse_type(self, spec, decl=None):
        symbol = self.table.lookup(spec.type)
        if not symbol or symbol.kind != SymbolKind.TYPE:
            self.raise_error(f"未声明的类型 '{spec.type}'", spec)
            return None

        type = symbol.type
        if not decl:
            return type
        if decl.pointer:
            type = PointerType(type)
        for suffix in reversed(decl.suffix):
            if isinstance(suffix, ArraySuffix):
                size = None
                if suffix.size:
                    self.visit(suffix.size)
                    if suffix.size.ctype == INT:
                        size = self.parse_constexpr(suffix.size)
                        if size is None:
                            self.raise_error("数组大小必须是常量表达式", suffix.size)
                    else:
                        self.raise_error("数组大小必须是 'int' 类型", suffix.size)
                type = ArrayType(type, size)
        return type


    def parse_constexpr(self, node):
        if isinstance(node, Integer):
            return int(node.value, 0)
        if isinstance(node, Identifier):
            symbol = self.table.lookup(node.value)
            if symbol and isinstance(symbol.type, EnumType):
                return symbol.type.enumerators[symbol.name]
        if isinstance(node, BinaryOp):
            left = self.parse_constexpr(node.left)
            right = self.parse_constexpr(node.right)
            if left is None or right is None:
                return None
            if node.op == '+':
                return left + right
            if node.op == '-':
                return left - right
            if node.op == '*':
                return left * right
            if node.op == '/':
                if right == 0:
                    self.raise_error("常量表达式中不能除以0", node.right)
                return left // right
            if node.op == '%':
                if right == 0:
                    self.raise_error("常量表达式中不能对0取模", node.right)
                return left % right
            if node.op == '==':
                return int(left == right)
            if node.op == '!=':
                return int(left != right)
            if node.op == '<':
                return int(left < right)
            if node.op == '>':
                return int(left > right)
            if node.op == '<=':
                return int(left <= right)
            if node.op == '>=':
                return int(left >= right)
            if node.op == '&&':
                return int(bool(left) and bool(right))
            if node.op == '||':
                return int(bool(left) or bool(right))
        if isinstance(node, UnaryOp):
            operand = self.parse_constexpr(node.operand)
            if operand is None:
                return None
            if node.op == '+':
                return operand
            if node.op == '-':
                return -operand
            if node.op == '!':
                return int(not operand)
        return None


    def parse_init(self, node, type, context):
        if isinstance(type, ArrayType):
            if type.size is not None and len(node.inits) > type.size:
                msg = f"数组 '{context.name.value}' 的初始化项长度 '{len(node.inits)}' 超出数组大小 '{type.size}'"
                self.raise_error(msg, context)
            elif type.size is None:
                type.size = len(node.inits)

            type = type.type
            for init in node.inits:
                if isinstance(init, Initializer):
                    self.parse_init(init, type, context)
                else:
                    self.visit(init)
                    if not self.is_assignable(type, init.ctype):
                        self.raise_error(f"无法将 '{init.ctype}' 初始化为 '{type}'", init)
        elif isinstance(type, CompoundType):
            types = list(type.members.values())

            if len(node.inits) > len(types):
                self.raise_error(f"类型 '{type}' 的初始化项过多", node)

            for init, member_type in zip(node.inits, types):
                if isinstance(init, Initializer):
                    self.parse_init(init, member_type, context)
                else:
                    self.visit(init)
                    if not self.is_assignable(member_type, init.ctype):
                        self.raise_error(f"无法将 '{init.ctype}' 初始化为 '{member_type}'", init)
        else:
            self.raise_error(f"初始化列表不能用于类型 '{type}'", node)


    @staticmethod
    def parse_op(op, ltype, rtype):
        if op in ('+', '-', '*', '/'):
            if isinstance(ltype, PointerType) and rtype == INT:
                return ltype
            if op == '+' and ltype == INT and isinstance(rtype, PointerType):
                return rtype
            if op == '-' and isinstance(ltype, PointerType) and isinstance(rtype, PointerType) and ltype == rtype:
                return INT
            if ltype == FLOAT or rtype == FLOAT:
                return FLOAT
            if ltype == INT and rtype == INT:
                return INT
        elif op == '%':
            if ltype == INT and rtype == INT:
                return INT
        elif op in ('<', '>', '<=', '>=', '==', '!=', '&&', '||'):
            is_arith = lambda t: t in [INT, FLOAT, CHAR, BOOL]
            if is_arith(ltype) and is_arith(rtype):
                return BOOL
            elif isinstance(ltype, (PointerType, ArrayType)) and ltype == rtype:
                return BOOL
            elif isinstance(ltype, PointerType) and rtype == NULL:
                return BOOL
            elif ltype == NULL and isinstance(rtype, PointerType):
                return BOOL
        return None


    @staticmethod
    def is_assignable(ltype, rtype):
        if ltype == rtype:
            return True
        if isinstance(ltype, EnumType) and rtype == INT or ltype == INT and isinstance(rtype, EnumType):
            return True
        if ltype == BOOL and (isinstance(rtype, (BasicType, PointerType, ArrayType))):
            return True
        if ltype == FLOAT and rtype == INT:
            return True
        if isinstance(ltype, PointerType) and rtype == NULL:
            return True
        if isinstance(ltype, PointerType) and isinstance(rtype, ArrayType) and ltype.type == rtype.type:
            return True
        if isinstance(ltype, PointerType) and ltype.type == VOID and isinstance(rtype, (PointerType, ArrayType)):
            return True
        return False

    def is_lvalue(self, node):
        if isinstance(node, UnaryOp) and node.op == '*':
            return True
        if isinstance(node, (Identifier, ArrayAccess, MemberAccess)):
            if isinstance(node, Identifier):
                symbol = self.table.lookup(node.value)
                if symbol and symbol.kind == SymbolKind.CONST:
                    return False
            return True
        return False

    # ===============  访问方法  ===============

    def program(self, tree):
        self.visit(tree.decl)

    def declaration(self, tree):
        for decl in tree.decls:
            self.visit(decl)

    def func_def(self, tree):
        return_type = self.parse_type(tree.spec)
        func_name = tree.decl.name.value

        suffix = next(i for i in tree.decl.suffix if isinstance(i, ParamSuffix))
        param_types, param_names = [], []
        if suffix.params and suffix.params != ['void']:
            for param in suffix.params:
                param_type = self.parse_type(param.spec, param.decl)
                param_name = param.decl.name.value
                param_types.append(param_type)
                param_names.append((param_type, param_name, param))

        func_type = FunctionType(return_type, param_types)
        symbol = self.table.lookup(func_name)
        if symbol:
            if symbol.defined:
                self.raise_error(f"函数 '{func_name}' 重复定义", tree.decl.name)
                return
            if symbol.type != func_type:
                self.raise_error(f"函数 '{func_name}' 类型冲突", tree.decl.name)
                return
            symbol.node = tree
            symbol.defined = True
        else:
            symbol = Symbol(func_type, func_name, SymbolKind.FUNC, tree.decl.name)
            if not self.table.define(symbol):
                self.raise_error(f"函数 '{func_name}' 重复定义", tree.decl.name)

        tree.decl.name.symbol = symbol
        tree.ctype = func_type
        self.curr_func = func_type
        self.table.enter_scope()

        for param_type, param_name, node in param_names:
            symbol = Symbol(param_type, param_name, SymbolKind.VAR, node.decl.name)
            if not self.table.define(symbol):
                self.raise_error(f"形参 '{param_name}' 重复定义", node)

        self.visit(tree.body)

        self.table.leave_scope()
        self.curr_func = None

    def comp_def(self, tree):
        comp_name = tree.decl.name.value
        is_union = False if tree.spec.type == 'struct' else True

        temp_type = CompoundType(comp_name, None, is_union)
        symbol = Symbol(temp_type, comp_name, SymbolKind.TYPE, tree.decl.name, defined=False)
        if not self.table.define(symbol):
            self.raise_error(f"类型 '{comp_name}' 重复定义", tree.decl.name)

        members = {}
        for member in tree.members:
            for member_decl in member.decls:
                member_name = member_decl.name.value
                if member_name in members:
                    self.raise_error(f"成员变量 '{member_name}' 重复定义", member_decl)
                member_type = self.parse_type(member.spec, member_decl)
                members[member_name] = member_type
                member_decl.ctype = member_type

        comp_type = CompoundType(comp_name, members, is_union)
        symbol.type = comp_type
        symbol.defined = True

    def enum_def(self, tree):
        enum_name = tree.decl.name.value

        if self.table.lookup(enum_name):
            self.raise_error(f"枚举 '{enum_name}' 重复定义", tree.name)
            return

        enumerators, cnt = {}, 0
        for enumerator in tree.enumerators:
            imm_name = enumerator.name.value
            if self.table.lookup(imm_name) or imm_name in enumerators:
                self.raise_error(f"枚举常量 '{imm_name}' 重复定义", enumerator.name)
                return

            if enumerator.value:
                self.visit(enumerator.value)
                value = self.parse_constexpr(enumerator.value)
                if value is None:
                    self.raise_error(f"枚举常量 '{imm_name}' 必须是常量表达式", enumerator.value)
                    return
                cnt = value

            enumerators[imm_name] = cnt
            cnt += 1

        enum_type = EnumType(enum_name, enumerators)
        symbol = Symbol(enum_type, enum_name, SymbolKind.TYPE, tree.decl.name)
        self.table.define(symbol)

        for enumerator in tree.enumerators:
            imm_name = enumerator.name.value
            symbol = Symbol(enum_type, imm_name, SymbolKind.CONST, enumerator.name)
            self.table.define(symbol)

    def func_decl(self, tree):
        return_type = self.parse_type(tree.spec)

        for decl in tree.decls:
            func_name = decl.name.value

            suffix = next((i for i in decl.suffix if isinstance(i, ParamSuffix)), None)
            params_types = []
            if suffix.params and suffix.params != ['void']:
                for param in suffix.params:
                    param_type = self.parse_type(param.spec, param.decl)
                    if param_type:
                        params_types.append(param_type)

            func_type = FunctionType(return_type, params_types)
            symbol = self.table.lookup(func_name)
            if symbol:
                if symbol.type != func_type:
                    self.raise_error(f"函数 '{func_name}' 类型冲突", decl.name)
                else:
                    self.raise_error(f"函数 '{func_name}' 重复定义", decl.name)
            else:
                symbol = Symbol(func_type, func_name, SymbolKind.FUNC, decl.name, defined=False)
                self.table.define(symbol)
            decl.ctype = func_type

    def var_decl(self, tree):
        for decl in tree.decls:
            var_type = self.parse_type(tree.spec, decl)
            var_name = decl.name.value
            var_init = decl.init

            decl.ctype = var_type
            if var_type == VOID:
                self.raise_error(f"变量 '{var_name}' 不能被声明为 'void' 类型", decl.name)
                return

            symbol = Symbol(var_type, var_name, SymbolKind.VAR, decl.name)
            if not self.table.define(symbol):
                self.raise_error(f"变量 '{var_name}' 重复定义", decl.name)

            if var_init:
                self.visit(var_init)
                if isinstance(var_init, Initializer):
                    self.parse_init(var_init, var_type, decl)
                elif self.curr_func is None and self.parse_constexpr(var_init) is None:
                    self.raise_error(f"全局变量 '{var_name}' 的初始化项必须是常量表达式", var_init)
                elif not self.is_assignable(var_type, var_init.ctype):
                    self.raise_error(f"无法将 '{var_init.ctype}' 初始化为 '{var_type}'", var_init)


    def arr_decl(self, tree):
        for decl in tree.decls:
            arr_type = self.parse_type(tree.spec, decl)
            arr_name = decl.name.value
            arr_init = decl.init

            decl.ctype = arr_type
            if arr_type.size is None and arr_init is None:
                self.raise_error(f"数组 '{arr_name}' 没有初始化列表", decl)
                return
            if arr_type.type == VOID:
                self.raise_error(f"数组 '{arr_name}' 不能被声明为 'void' 类型", decl.name)
                return

            symbol = Symbol(arr_type, decl.name.value, SymbolKind.VAR, decl.name)
            if not self.table.define(symbol):
                self.raise_error(f"数组 '{arr_name}' 重复定义", decl.name)

            if arr_init:
                self.visit(arr_init)
                if isinstance(arr_init, Initializer):
                    self.parse_init(arr_init, arr_type, decl)
                elif not self.is_assignable(arr_type, arr_init.ctype):
                    self.raise_error(f"无法将 '{arr_init.ctype}' 初始化为 '{arr_type}'", arr_init)


    def statement(self, tree):
        self.table.enter_scope()
        for stmt in tree.stmts:
            self.visit(stmt)
        self.table.leave_scope()

    def if_stmt(self, tree):
        self.visit(tree.cond)
        if not self.is_assignable(BOOL, tree.cond.ctype):
            self.raise_error("条件表达式的类型必须能转换为布尔型", tree.cond)
        self.visit(tree.then)
        if tree.orelse:
            self.visit(tree.orelse)

    def while_stmt(self, tree):
        self.loop_depth += 1
        self.visit(tree.cond)
        if not self.is_assignable(BOOL, tree.cond.ctype):
            self.raise_error("条件表达式的类型必须能转换为布尔型", tree.cond)
        self.visit(tree.body)
        self.loop_depth -= 1

    def for_stmt(self, tree):
        self.table.enter_scope()
        self.loop_depth += 1
        if tree.init:
            self.visit(tree.init)
        if tree.cond:
            self.visit(tree.cond)
            if not self.is_assignable(BOOL, tree.cond.ctype):
                self.raise_error("条件表达式的类型必须能转换为布尔型", tree.cond)
        if tree.post:
            self.visit(tree.post)
        self.visit(tree.body)
        self.loop_depth -= 1
        self.table.leave_scope()

    def return_stmt(self, tree):
        if tree.expr:
            self.visit(tree.expr)

        if not self.curr_func:
            self.raise_error("'return' 语句只能出现在函数内部", tree)
            return

        type = self.curr_func.type
        if tree.expr:
            if type == VOID:
                self.raise_error("void 函数不能有返回值", tree)
            elif not self.is_assignable(type, tree.expr.ctype):
                self.raise_error(f"函数期望返回 '{type}' 而非 '{tree.expr.ctype}'", tree.expr)
        elif type != VOID:
            self.raise_error(f"函数期望返回 '{type}'", tree)

    def break_stmt(self, tree):
        if self.loop_depth == 0:
            self.raise_error("'break' 语句只能出现在循环内部", tree)

    def continue_stmt(self, tree):
        if self.loop_depth == 0:
            self.raise_error("'continue' 语句只能出现在循环内部", tree)

    def empty_stmt(self, tree):
        pass

    def expr_stmt(self, tree):
        if tree.expr:
            self.visit(tree.expr)

    def expression(self, tree):
        for expr in tree.exprs:
            self.visit(expr)
        if tree.exprs:
            tree.ctype = tree.exprs[-1].ctype


    def assign_op(self, tree):
        self.visit(tree.left)
        self.visit(tree.right)
        if not self.is_lvalue(tree.left):
            self.raise_error("表达式无法赋值", tree.left)
            return
        if hasattr(tree.left, 'ctype') and hasattr(tree.right, 'ctype'):
            ltype, rtype = tree.left.ctype, tree.right.ctype
            if tree.op == '=':
                if not self.is_assignable(ltype, rtype):
                    self.raise_error(f"无法将 '{rtype}' 赋值给 '{ltype}'", tree)
            else:
                op = tree.op[:-1]
                ctype = self.parse_op(op, ltype, rtype)
                if not ctype:
                    self.raise_error(f"运算符 '{tree.op}' 无效", tree)
                elif not self.is_assignable(ltype, ctype):
                    self.raise_error(f"无法将 '{rtype}' 赋值给 '{ltype}'", tree)
            tree.ctype = ltype

    def binary_op(self, tree):
        self.visit(tree.left)
        self.visit(tree.right)
        ctype = self.parse_op(tree.op, tree.left.ctype, tree.right.ctype)
        if ctype is None:
            self.raise_error(f"运算符 '{tree.op}' 无效", tree)
        else:
            tree.ctype = ctype


    def unary_op(self, tree):
        self.visit(tree.operand)
        ctype, op = tree.operand.ctype, tree.op
        if op in ('+', '-'):
            if ctype in (INT, FLOAT):
                tree.ctype = ctype
            else:
                self.raise_error(f"运算符 '{op}' 的操作数必须是数值类型而非 '{ctype}'", tree.operand)
        elif op == '!':
            if self.is_assignable(BOOL, ctype):
                tree.ctype = BOOL
            else:
                self.raise_error(f"运算符 '{op}' 的操作数能转换为 'bool' 而非 '{ctype}'", tree.operand)
        elif op == '*':
            if isinstance(ctype, PointerType):
                tree.ctype = ctype.type
            elif isinstance(ctype, ArrayType):
                tree.ctype = ctype.type
            else:
                self.raise_error(f"运算符 '{op}' 只能用于指针或数组类型而非 '{ctype}'", tree.operand)
        elif op == '&':
            if self.is_lvalue(tree.operand):
                tree.ctype = PointerType(ctype)
            else:
                self.raise_error(f"运算符 '{op}' 只能用于可修改的左值", tree.operand)
        elif op in ('++', '--'):
            if self.is_lvalue(tree.operand) and (ctype in (INT, FLOAT) or isinstance(ctype, PointerType)):
                tree.ctype = ctype
            else:
                self.raise_error(f"运算符 '{op}' 的操作数必须是可修改的值或指针左值", tree.operand)

    def postfix_op(self, tree):
        self.visit(tree.operand)
        ctype = tree.operand.ctype
        if self.is_lvalue(tree.operand) and (ctype in (INT, FLOAT) or isinstance(ctype, PointerType)):
            tree.ctype = ctype
        else:
            self.raise_error(f"运算符 '{tree.op}' 的操作数必须是可修改的值或指针左值", tree.operand)

    def func_call(self, tree):
        self.visit(tree.func)
        for arg in tree.args:
            self.visit(arg)
        ctype = tree.func.ctype
        if not isinstance(ctype, FunctionType):
            self.raise_error("无法调用表达式", tree.func)
        args = [arg.ctype for arg in tree.args]
        if len(args) != len(ctype.params):
            self.raise_error(f"函数调用参数数量期望 '{len(ctype.params)}' 个而非 '{len(args)}' 个", tree)
        else:
            for i, (arg, param) in enumerate(zip(args, ctype.params)):
                if not self.is_assignable(param, arg):
                    self.raise_error(f"函数调用第 {i + 1} 个参数类型期望 '{param}' 而非 {arg}", tree.args[i])
        tree.ctype = ctype.type

    def array_access(self, tree):
        self.visit(tree.array)
        self.visit(tree.index)
        array_type, index = tree.array.ctype, tree.index.ctype
        if index != INT:
            self.raise_error("数组下标必须是整数类型", tree.index)
        if isinstance(array_type, ArrayType):
            tree.ctype = array_type.type
        elif isinstance(array_type, PointerType):
            tree.ctype = array_type.type
        else:
            self.raise_error(f"运算符 '[]' 只能用于指针或数组类型而非 '{array_type}'", tree)

    def member_access(self, tree):
        self.visit(tree.object)

        obj_type, member_name = tree.object.ctype, tree.member.value
        if tree.arrow:
            if isinstance(obj_type, PointerType) and isinstance(obj_type.type, CompoundType):
                comp_type = obj_type.type
            else:
                self.raise_error(f"运算符 '->' 必须用于指向结构体或联合体的指针而非 '{obj_type}'", tree.object)
                return
        else:
            if isinstance(obj_type, CompoundType):
                comp_type = obj_type
            else:
                self.raise_error(f"运算符 '.' 必须用于结构体或联合体而非 '{obj_type}'", tree.object)
                return
        if member_name in comp_type.members:
            tree.ctype = comp_type.members[member_name]
            tree.member.ctype = tree.ctype
            tree.index = list(comp_type.members.keys()).index(member_name)
        else:
            self.raise_error(f"类型 '{comp_type}' 中不存在名为 '{member_name}' 的成员", tree.member)

    def identifier(self, tree):
        symbol = self.table.lookup(tree.value)
        if not symbol:
            self.raise_error(f"未声明的标识符 '{tree.value}'", tree)
            return
        tree.ctype = symbol.type
        tree.symbol = symbol

    @staticmethod
    def integer(tree):
        tree.ctype = INT

    @staticmethod
    def decimal(tree):
        tree.ctype = FLOAT

    @staticmethod
    def character(tree):
        tree.ctype = CHAR

    @staticmethod
    def string(tree):
        tree.ctype = ArrayType(CHAR)

    @staticmethod
    def bool(tree):
        tree.ctype = BOOL

    @staticmethod
    def nullptr(tree):
        tree.ctype = NULL

    def __default__(self, tree):
        for child in tree.children:
            if isinstance(child, Tree):
                self.visit(child)
