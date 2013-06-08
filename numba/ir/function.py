# -*- coding: utf-8 -*-

"""
Flow graph and operation for programs.
"""

from __future__ import print_function, division, absolute_import

import types
import collections

from numba.utils import WriteOnceTypedProperty

# ______________________________________________________________________

def make_temper():
    temps = collections.defaultdict(int)

    def temper(name):
        count = temps[name]
        temps[name] += 1
        if name and count == 0:
            return name
        elif name:
            return '%s_%d' % (name, count)
        else:
            return str(count)

    return temper

# ______________________________________________________________________

class FunctionGraph(object):

    def __init__(self, name, blocks=None, temper=None):
        self.name = name

        # Basic blocks in topological order
        self.blocks = blocks or []

        # name -> temp_name
        self.temper = temper or make_temper()

    def __repr__(self):
        return "FunctionGraph(%s)" % self.blocks

class Block(object):

    def __init__(self, label):
        self.label = label   # unique label
        self.parent = None   # FunctionGraph that owns us
        self.instrs = []     # [Operation | Constant]

    def __iter__(self):
        return iter(self.instrs)

    def append(self, instr):
        self.instrs.append(instr)

    def extend(self, instrs):
        self.instrs.extend(instrs)

    def __repr__(self):
        return "Block(%s, %s, %s)" % (self.id, self.label, self.instrs)

# ______________________________________________________________________

class Value(object):
    __slots__ = ("opcode", "type", "args", "result")

class Operation(Value):
    """
    We can employ two models:

        1) operation(result, opcode, args)

            Each operation has a result/target/variable.
            We can retrieve the operations you refer to through
            a variable store: { name : Operation } (i.e. use -> def)

            ops_x = {}
            for block in blocks:
                for i, op in enumerate(block.ops):
                    if op == 'X':
                        ops_x[op.result] = op
                    elif op == 'Y' and op.args[0] in ops_x:
                        x_arg = ops_x[op.args[0]]
                        block.ops[i] = Operation('Z', op.args, op.result)

        2) operation(opcode, args)

            Each operation is either a result/target/variable (LLVM) or
            a Value has an operation.

                class Value:
                    Use *UseList
                    Type type

                class User(Value):
                    Use *OperandList

            Example:

                %0 = X()            # oplist=[] uselist=[%2]
                %1 = Y()            # oplist=[] uselist=[%2]
                %2 = Z(%0, %1)      # oplist=[%0, %1] uselist=[]

            At any point we can efficiently match a pattern Z(X(), *):
    """

    def __init__(self, opcode, type, args, result=None):
        self.opcode = opcode
        self.type = type
        self.args = args # [Operation | Constant]
        self.result = result

    def replace(self, opcode, args):
        self.opcode = opcode
        self.args = args

    def __repr__(self):
        args = [arg.result for arg in self.args]
        return "Operation(%s, %s)" % (self.opcode, args)

class Constant(Value):
    """
    Constant value.
    """

    opcode = WriteOnceTypedProperty(types.NoneType, "Opcode")
    type = WriteOnceTypedProperty(types.NoneType, "Type")
    args = WriteOnceTypedProperty(list, "Args list")
    const = WriteOnceTypedProperty(object, "Constant value")
    result = WriteOnceTypedProperty(types.NoneType, "Result")

    def __init__(self, pyval):
        self.opcode = None
        self.args = [pyval]
        # self.const = pyval
        self.result = None

    def replace(self, opcode, args):
        raise RuntimeError("Constants cannot be replaced")

    @property
    def const(self):
        const, = self.args
        return const

    def __repr__(self):
        args = [arg.result for arg in self.args]
        return "Constant(%s)" % (self.const,)