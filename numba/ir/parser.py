# -*- coding: utf-8 -*-

"""
Parse numba IR.
"""

from __future__ import print_function, division, absolute_import

from lepl import *

def lit(name):
    return Drop(Literal(name))

class ParserActions(object):
    def __init__(self):
        self.stats = []
        self.argtypes = []
        self.argnames = []

    def p_header(self, args):
        name, arglist = args[0], args[1:]
        self.funcname = name
        for typename, argname in arglist:
            self.argtypes.append(typename)
            self.argnames.append(argname)

    def p_stat(self, args):
        dest, opname, type, arglist = args
        self.stats.append((dest, opname, type, arglist))

par = lambda value: lit("(") & value & lit(")")

ws = ~Whitespace()[:]
nl = ~Newline()
ident = Regexp("[a-zA-Z0-9_]+")
value = lit("%") & ident

def parse(actions):
    # TODO: Parse grammar as a string and then use lepl
    with Separator(ws):
        type = ident
        arg = type & value >List
        args = Optional(arg) & Star(lit(",") & arg)
        arglist = par(args)
        header = lit("function") & ident & arglist >actions.p_header
        statargs = arglist >List
        stat = value & lit("=") & par(type) & ident & statargs >actions.p_stat
        stats = Star((stat|ws) & nl)
        function = header & lit("{") & nl & stats & lit("}") & ws

    print(function.parse("""function func(int %foo) {
        %1 = (double) foo(int %foo)
    }
    """))

parse(ParserActions())