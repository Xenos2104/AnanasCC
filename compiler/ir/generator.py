import codecs
from pathlib import Path

from lark.visitors import Interpreter
from llvmlite import ir, binding

from compiler.semantic.symbol import *
from compiler.semantic.type import *
from compiler.tree import *
from compiler.utils import write_file

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()


class Generator(Interpreter):
    def __init__(self):
        super().__init__()
        self.module = ir.Module(name='main_module')
        self.builder = None
        self.ir = None

        self.curr_func = None
        self.loop_stack = []
        self.strings = {}
        self.structs = {}

        void_type = ir.IntType(8).as_pointer()
        func_type = ir.FunctionType(ir.IntType(32), [void_type], var_arg=True)
        ir.Function(self.module, func_type, name="printf")
        ir.Function(self.module, func_type, name="scanf")

        self.module.triple = 'x86_64-pc-windows-msvc19.44.35209'

    # ===============  基础方法  ===============

    def generate(self, tree):
        self.visit(tree)
        self.ir = str(self.module)
        try:
            mod = binding.parse_assembly(self.ir)
            mod.verify()
        except RuntimeError as e:
            print("IR报错了！！！！不！！！！！！！！！")
            raise e
        return self.ir

    def save(self, file_path=''):
        write_file(self.ir, Path(file_path) / '04 org_ir.txt')

    # ===============  辅助方法  ===============

    def get_type(self, ctype):
        if isinstance(ctype, BasicType):
            if ctype == VOID:
                return ir.VoidType()
            elif ctype == INT:
                return ir.IntType(32)
            elif ctype == FLOAT:
                return ir.FloatType()
            elif ctype == CHAR:
                return ir.IntType(8)
            elif ctype == BOOL:
                return ir.IntType(1)
            elif ctype == NULL:
                return ir.IntType(8).as_pointer()
        elif isinstance(ctype, PointerType):
            return self.get_type(ctype.type).as_pointer()
        elif isinstance(ctype, ArrayType):
            elem_type = self.get_type(ctype.type)
            size = ctype.size if ctype.size is not None else 0
            return ir.ArrayType(elem_type, size)
        elif isinstance(ctype, FunctionType):
            return_type = self.get_type(ctype.type)
            param_types = [self.get_type(p) for p in ctype.params]
            return ir.FunctionType(return_type, param_types)
        elif isinstance(ctype, CompoundType):
            if ctype.name in self.structs:
                return self.structs[ctype.name]
            struct_type = self.module.context.get_identified_type(ctype.name)
            self.structs[ctype.name] = struct_type
            member_types = [self.get_type(m) for m in ctype.members.values()]
            if ctype.union:
                largest_member = max(member_types, key=lambda m: m.get_abi_size(self.module.data_layout))
                struct_type.set_body(largest_member)
            else:
                struct_type.set_body(*member_types)
            return struct_type
        elif isinstance(ctype, EnumType):
            return ir.IntType(32)
        raise Exception

    def get_address(self, node):
        if isinstance(node, Identifier):
            return node.symbol.value
        elif isinstance(node, ArrayAccess):
            arr_addr = self.get_address(node.array)
            arr_idx = self.visit(node.index)
            indices = [ir.Constant(ir.IntType(32), 0), arr_idx]
            return self.builder.gep(arr_addr, indices, inbounds=True)
        elif isinstance(node, MemberAccess):
            obj_addr = self.get_address(node.object)
            obj_idx = node.index
            indices = [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), obj_idx)]
            return self.builder.gep(obj_addr, indices, inbounds=True)
        if isinstance(node, UnaryOp) and node.op == '*':
            return self.visit(node.operand)
        raise Exception

    def parse_string(self, node):
        if node.value in self.strings:
            return self.strings[node.value]

        unescaped_value = codecs.decode(node.value, 'unicode_escape')
        terminated_value = unescaped_value + '\0'

        str_arr = bytearray(terminated_value.encode('utf8'))
        str_type = ir.ArrayType(ir.IntType(8), len(str_arr))
        str_name = f".str.{len(self.strings)}"
        str_val = ir.GlobalVariable(self.module, str_type, name=str_name)
        str_val.initializer = ir.Constant(str_type, str_arr)
        str_val.global_constant = True
        str_val.linkage = 'private'

        self.strings[node.value] = str_val
        return str_val

    def parse_constant(self, node):
        if isinstance(node, Integer):
            return ir.Constant(ir.IntType(32), int(node.value, 0))
        if isinstance(node, Decimal):
            return ir.Constant(ir.FloatType(), float(node.value))
        if isinstance(node, Character):
            char_val =  codecs.decode(node.value, 'unicode_escape')
            return ir.Constant(ir.IntType(8), ord(char_val))
        if isinstance(node, Bool):
            return ir.Constant(ir.IntType(1), 1 if node.value else 0)
        if isinstance(node, NullPtr):
            return ir.Constant(ir.IntType(8).as_pointer(), None)
        if isinstance(node, String):
            return self.parse_string(node)
        if isinstance(node, Initializer):
            constants = [self.parse_constant(init) for init in node.inits]
            return constants
        raise Exception

    def parse_cast(self, value, tgt_type, signed=True):
        src_type = value.type
        if src_type == tgt_type:
            return value
        elif isinstance(src_type, ir.FloatType) and isinstance(tgt_type, ir.IntType):
            return self.builder.fptosi(value, tgt_type) if signed else self.builder.fptoui(value, tgt_type)
        elif isinstance(src_type, ir.IntType) and isinstance(tgt_type, ir.FloatType):
            return self.builder.sitofp(value, tgt_type) if signed else self.builder.uitofp(value, tgt_type)
        elif isinstance(src_type, ir.IntType) and isinstance(tgt_type, ir.IntType):
            if src_type.width < tgt_type.width:
                return self.builder.sext(value, tgt_type) if signed else self.builder.zext(value, tgt_type)
            else:
                return self.builder.trunc(value, tgt_type)
        elif isinstance(src_type, ir.PointerType) and isinstance(tgt_type, ir.PointerType):
            return self.builder.bitcast(value, tgt_type)
        elif isinstance(tgt_type, (ir.IntType, ir.PointerType)):
            return self.builder.bitcast(value, tgt_type)
        return value

    def parse_binary(self, tree, left, right):
        op = tree.op
        left_type, right_type = tree.left.ctype, tree.right.ctype

        if isinstance(left_type, BasicType) and isinstance(right_type, BasicType):
            if left_type == FLOAT or right_type == FLOAT:
                if left_type == INT:
                    left = self.builder.sitofp(left, ir.FloatType())
                if right_type == INT:
                    right = self.builder.sitofp(right, ir.FloatType())

        if op == '+' and isinstance(left_type, PointerType) and right_type == INT:
            return self.builder.gep(left, [right], inbounds=False)
        if op == '+' and left_type == INT and isinstance(right_type, PointerType):
            return self.builder.gep(right, [left], inbounds=False)
        if op == '-' and isinstance(left_type, PointerType) and right_type == INT:
            neg_val = self.builder.neg(right)
            return self.builder.gep(left, [neg_val], inbounds=False)
        if op == '-' and isinstance(left_type, PointerType) and isinstance(right_type, PointerType):
            diff1 = self.builder.ptrtoint(left, ir.IntType(64))
            diff2 = self.builder.ptrtoint(right, ir.IntType(64))
            res_val = self.builder.sub(diff1, diff2)
            return self.builder.trunc(res_val, ir.IntType(32))

        is_float = isinstance(left.type, ir.FloatType)
        if op in ('+', '-'):
            return self.builder.fadd(left, right) if is_float else self.builder.add(left, right)
        if op == '*':
            return self.builder.fmul(left, right) if is_float else self.builder.mul(left, right)
        if op == '/':
            return self.builder.fdiv(left, right) if is_float else self.builder.sdiv(left, right)
        if op == '%':
            return self.builder.srem(left, right)

        if op in ('==', '!=', '<', '>', '<=', '>='):
            return self.builder.fcmp_ordered(op, left, right) if is_float else self.builder.icmp_signed(op, left, right)
        if op == '&&':
            return self.builder.and_(left, right)
        if op == '||':
            return self.builder.or_(left, right)

        raise Exception

    def parse_init(self, values, tgt_addr):
        for i, item_val in enumerate(values):
            indices = [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)]
            elem_addr = self.builder.gep(tgt_addr, indices, inbounds=True)

            if isinstance(item_val, list):
                self.parse_init(item_val, elem_addr)
            else:
                tgt_type = elem_addr.type.pointee

                cond_decay = (isinstance(item_val, ir.GlobalVariable) and
                              isinstance(item_val.type.pointee, ir.ArrayType) and
                              isinstance(elem_addr.type.pointee, ir.PointerType))
                cond_null = (isinstance(item_val, ir.Constant) and
                             item_val.type.is_pointer and
                             str(item_val).endswith('null'))

                if cond_decay:
                    zero = ir.Constant(ir.IntType(32), 0)
                    item_val = self.builder.gep(item_val, [zero, zero], inbounds=True)
                elif cond_null:
                    if isinstance(tgt_type, ir.PointerType):
                        item_val = ir.Constant(tgt_type, None)
                    else:
                        raise Exception
                elif item_val.type != tgt_type:
                    item_val = self.parse_cast(item_val, tgt_type)

                self.builder.store(item_val, elem_addr)

    # ===============  访问方法  ===============

    def program(self, tree: Program):
        self.visit(tree.decl)

    def declaration(self, tree):
        for decl in tree.decls:
            self.visit(decl)

    def func_def(self, tree):
        func_name = tree.decl.name.value

        if func_name in self.module.globals:
            self.curr_func = self.module.globals[func_name]
        else:
            func_type = self.get_type(tree.ctype)
            self.curr_func = ir.Function(self.module, func_type, name=func_name)
        tree.decl.name.symbol.value = self.curr_func

        block = self.curr_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        for i, arg in enumerate(self.curr_func.args):
            param = tree.decl.suffix[0].params[i]
            arg.name = param.decl.name.value

            param_addr = self.builder.alloca(arg.type, name=f"{arg.name}.addr")
            param.decl.name.symbol.value = param_addr
            self.builder.store(arg, param_addr)

        self.visit(tree.body)

        if not self.builder.block.is_terminated:
            if tree.ctype.type == VOID:
                self.builder.ret_void()
            else:
                self.builder.unreachable()

        self.curr_func = None

    def comp_def(self, tree):
        pass

    def enum_def(self, tree):
        pass


    def var_decl(self, tree):
        for decl in tree.decls:
            var_name = decl.name.value
            var_type = self.get_type(decl.ctype)

            if self.curr_func:
                var_addr = self.builder.alloca(var_type, name=var_name)
                decl.name.symbol.value = var_addr
                if decl.init:
                    init_val = self.visit(decl.init)
                    if isinstance(decl.init, Initializer):
                        self.parse_init(init_val, var_addr)
                    else:
                        casted_val = self.parse_cast(init_val, var_type)
                        self.builder.store(casted_val, var_addr)
            else:
                var_val = ir.GlobalVariable(self.module, var_type, name=var_name)
                decl.name.symbol.value = var_val
                if decl.init:
                    const_val = self.parse_constant(decl.init)
                    if isinstance(const_val, list):
                        var_val.initializer = ir.Constant(var_type, const_val)
                    else:
                        var_val.initializer = const_val
                else:
                    var_val.initializer = ir.Constant(var_type, None)


    def arr_decl(self, tree):
        return self.var_decl(tree)

    def func_decl(self, tree: FunctionDeclaration):
        for decl in tree.decls:
            func_name = decl.name.value
            if not self.module.globals.get(func_name):
                func_type = self.get_type(decl.ctype)
                self.curr_func = ir.Function(self.module, func_type, name=func_name)
                decl.name.symbol.value = self.curr_func

    def statement(self, tree):
        for stmt in tree.stmts:
            self.visit(stmt)

    def if_stmt(self, tree: IfStatement):
        cond_val = self.visit(tree.cond)

        if cond_val.type != ir.IntType(1):
            cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))

        if tree.orelse:
            with self.builder.if_else(cond_val) as (then, orelse):
                with then:
                    self.visit(tree.then)
                with orelse:
                    self.visit(tree.orelse)
        else:
            with self.builder.if_then(cond_val):
                self.visit(tree.then)

    def while_stmt(self, tree):
        cond_block = self.curr_func.append_basic_block('while.cond')
        loop_block = self.curr_func.append_basic_block('while.body')
        end_block = self.curr_func.append_basic_block('while.end')

        self.loop_stack.append((end_block, cond_block))
        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = self.visit(tree.cond)
        if cond_val.type != ir.IntType(1):
            cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, loop_block, end_block)

        self.builder.position_at_end(loop_block)
        self.visit(tree.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)
        self.loop_stack.pop()

    def for_stmt(self, tree):
        cond_block = self.curr_func.append_basic_block('for.cond')
        loop_block = self.curr_func.append_basic_block('for.body')
        post_block = self.curr_func.append_basic_block('for.post')
        end_block = self.curr_func.append_basic_block('for.end')

        self.loop_stack.append((end_block, post_block))
        if tree.init:
            self.visit(tree.init)
        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        if tree.cond:
            cond_val = self.visit(tree.cond)
            if cond_val.type != ir.IntType(1):
                cond_val = self.builder.icmp_signed('!=', cond_val, ir.Constant(cond_val.type, 0))
            self.builder.cbranch(cond_val, loop_block, end_block)
        else:
            self.builder.branch(loop_block)

        self.builder.position_at_end(loop_block)
        self.visit(tree.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(post_block)

        self.builder.position_at_end(post_block)
        if tree.post:
            self.visit(tree.post)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)
        self.loop_stack.pop()

    def return_stmt(self, tree):
        if tree.expr:
            return_val = self.visit(tree.expr)
            return_val = self.parse_cast(return_val, self.curr_func.return_value)
            self.builder.ret(return_val)
        else:
            self.builder.ret_void()

    def break_stmt(self, _):
        break_target = self.loop_stack[-1][0]
        self.builder.branch(break_target)

    def continue_stmt(self, _):
        continue_target = self.loop_stack[-1][1]
        self.builder.branch(continue_target)

    def empty_stmt(self, _):
        pass

    def expr_stmt(self, tree):
        if tree.expr:
            self.visit(tree.expr)

    def expression(self, tree: Expression):
        expr_val = None
        for expr in tree.exprs:
            expr_val = self.visit(expr)
        return expr_val

    def assign_op(self, tree):
        left_addr = self.get_address(tree.left)
        right_val = self.visit(tree.right)

        if tree.op == '=':
            res_val = self.parse_cast(right_val, left_addr.type.pointee)
            self.builder.store(res_val, left_addr)
            return res_val
        else:
            op = tree.op[:-1]
            left_val = self.builder.load(left_addr)

            fake_node = BinaryOp(op, None, None)
            fake_node.left = type("Fake", (), {"ctype": tree.left.ctype})()
            fake_node.right = type("Fake", (), {"ctype": tree.right.ctype})()

            res_val = self.parse_binary(fake_node, left_val, right_val)
            casted_val = self.parse_cast(res_val, left_addr.type.pointee)
            self.builder.store(casted_val, left_addr)
            return res_val

    def binary_op(self, tree):
        if tree.op in ('&&', '||'):
            is_and = (tree.op == '&&')

            left_cond = self.visit(tree.left)
            if left_cond.type != ir.IntType(1):
                left_cond = self.builder.icmp_ne(left_cond, ir.Constant(left_cond.type, 0))

            res_addr = self.builder.alloca(ir.IntType(1), name='logic.res')
            self.builder.store(left_cond, res_addr)

            next_block = self.curr_func.append_basic_block('logic.next')
            end_block = self.curr_func.append_basic_block('logic.end')
            self.builder.cbranch(left_cond, next_block if is_and else end_block, end_block if is_and else next_block)

            self.builder.position_at_end(next_block)
            right_cond = self.visit(tree.right)
            if right_cond.type != ir.IntType(1):
                right_cond = self.builder.icmp_ne(right_cond, ir.Constant(right_cond.type, 0))
            self.builder.store(right_cond, res_addr)
            self.builder.branch(end_block)

            self.builder.position_at_end(end_block)
            return self.builder.load(res_addr)
        else:
            left_val = self.visit(tree.left)
            right_val = self.visit(tree.right)
            return self.parse_binary(tree, left_val, right_val)

    def unary_op(self, tree):
        old_val = self.visit(tree.operand)
        if tree.op == '+':
            return old_val
        elif tree.op == '-':
            if isinstance(old_val.type, ir.FloatType):
                return self.builder.fneg(old_val)
            else:
                return self.builder.neg(old_val)
        elif tree.op == '!':
            zero = ir.Constant(old_val.type, 0)
            return self.builder.icmp_signed('==', old_val, zero)
        elif tree.op == '&':
            return self.get_address(tree.operand)
        elif tree.op == '*':
            return self.builder.load(old_val)
        elif tree.op in ('++', '--'):
            operand_addr = self.get_address(tree.operand)
            old_val = self.builder.load(operand_addr)
            one = ir.Constant(old_val.type, 1)
            new_val = self.builder.add(old_val, one) if tree.op == '++' else self.builder.sub(old_val, one)
            self.builder.store(new_val, operand_addr)
            return new_val
        raise Exception

    def postfix_op(self, tree):
        operand_addr = self.get_address(tree.operand)
        old_val = self.builder.load(operand_addr)
        one = ir.Constant(old_val.type, 1)
        new_val = self.builder.add(old_val, one) if tree.op == '++' else self.builder.sub(old_val, one)
        self.builder.store(new_val, operand_addr)
        return old_val

    def func_call(self, tree):
        func_name = tree.func.value
        if func_name in ("printf", "scanf"):
            func_val = self.module.globals.get(func_name)
            format_str_val = self.visit(tree.args[0])
            arg_vals = [format_str_val]

            for arg_node in tree.args[1:]:
                if func_name == 'printf':
                    arg_val = self.visit(arg_node)
                    if isinstance(arg_val.type, ir.FloatType):
                        arg_val = self.builder.fpext(arg_val, ir.DoubleType())
                    arg_vals.append(arg_val)

                elif func_name == 'scanf':
                    arg_addr = self.get_address(arg_node)
                    casted_addr = self.builder.bitcast(arg_addr, ir.IntType(8).as_pointer())
                    arg_vals.append(casted_addr)
            return self.builder.call(func_val, arg_vals)
        else:
            func_val = self.visit(tree.func)
            arg_vals = []
            for i, arg_node in enumerate(tree.args):
                arg_type = func_val.type.pointee.args[i]
                arg_val = self.visit(arg_node)
                arg_val = self.parse_cast(arg_val, arg_type)
                arg_vals.append(arg_val)
            return self.builder.call(func_val, arg_vals)

    def array_access(self, tree):
        elem_addr = self.get_address(tree)
        return self.builder.load(elem_addr)

    def member_access(self, tree):
        member_addr = self.get_address(tree)
        if isinstance(tree.object.ctype, CompoundType) and tree.object.ctype.union:
            target_ptr_type = self.get_type(tree.ctype).as_pointer()
            member_addr = self.builder.bitcast(member_addr, target_ptr_type)
        return self.builder.load(member_addr)

    def identifier(self, tree):
        symbol = tree.symbol
        if isinstance(symbol.type, (FunctionType, ArrayType)):
            return symbol.value
        if symbol.kind == SymbolKind.CONST and isinstance(symbol.type, EnumType):
            val = symbol.type.enumerators[symbol.name]
            return ir.Constant(ir.IntType(32), val)
        return self.builder.load(symbol.value)

    @staticmethod
    def integer(tree):
        return ir.Constant(ir.IntType(32), int(tree.value, 0))

    @staticmethod
    def decimal(tree):
        return ir.Constant(ir.FloatType(), float(tree.value))

    @staticmethod
    def character(tree):
        char_val = codecs.decode(tree.value, 'unicode_escape')
        return ir.Constant(ir.IntType(8), ord(char_val))

    def string(self, tree):
        str_val = self.parse_string(tree)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(str_val, [zero, zero], inbounds=True, name=f"{str_val.name}.decay")

    @staticmethod
    def bool(tree):
        return ir.Constant(ir.IntType(1), tree.value)

    @staticmethod
    def nullptr(_):
        return ir.Constant(ir.IntType(8).as_pointer(), None)

    def initializer(self, tree):
        return [self.visit(init) for init in tree.inits]

    def __default__(self, tree):
        raise Exception
