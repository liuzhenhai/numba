# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import ctypes
import types
from collections import namedtuple
from functools import partial
import math
import cmath

from .. import ltypes, llvm_support, linking, libs
from . import test_support

import numpy as np
from llvm.core import *
from llvm.ee import GenericValue

# ______________________________________________________________________

sinname = 'my_custom_sin'
cosname = 'my.custom.cos'
powname = 'my.special.pow'

namemap = {
    sinname: 'sin',
    cosname: 'cos',
    powname: 'pow',
}

def all_replacements():
    replacements = {}
    for name in namemap:
        for ty in ltypes.all_types:
            replacements[name + str(ty)] = namemap[name]

    return replacements

# ______________________________________________________________________

Ctx = namedtuple('Ctx', "engine module pm link")

def new_ctx(lib=None, linker=None):
    engine, mod, pm = test_support.make_llvm_context()
    replacements = all_replacements()

    if lib is None:
        lib = libs.get_mathlib_bc()
        linker = linking.LLVMLinker()

    link = partial(linking.link_llvm_math_intrinsics,
                   engine, mod, lib, linker, replacements)
    def verify():
        link()
        mod.verify()

    return Ctx(engine, mod, pm, verify)

# ______________________________________________________________________

def make_func(ctx, defname, callname, ty, nargs=1, byref=False):
    """
    Create an llvm function that calls an abstract math function. We
    use this to test linking, e.g. my_custom_sin(x) -> npy_sin(x)
    """
    fty = Type.function(ty, [ty] * nargs)
    wrapped = ctx.module.get_or_insert_function(fty, callname)
    if byref:
        wrap = test_support.create_byref_wrapper
    else:
        wrap = test_support.create_byval_wrapper

    return wrap(wrapped, defname)

#===------------------------------------------------------------------===
# Tests
#===------------------------------------------------------------------===

def test_link_real():
    ctx = new_ctx()
    def mkfunc(defname, callname, ty):
        return make_func(ctx, defname, callname + str(ty), ty)

    mkfunc('mysinf', sinname, ltypes.l_float)
    mkfunc('mysin',  sinname, ltypes.l_double)
    mkfunc('mysinl', sinname, ltypes.l_longdouble)

    # print(ctx.module)
    ctx.link()

    m = test_support.make_mod(ctx)
    our_result = m.mysinf(10.0), m.mysin(10.0), m.mysinl(10.0)
    exp_result = [math.sin(10.0)] * 3
    assert np.allclose(our_result, exp_result)

def test_link_complex():
    ctx = new_ctx()
    def mkfunc(defname, callname, ty):
        return make_func(ctx, defname, callname + str(ty), ty, byref=True)

    # NOTE: we can't reliably call our function. TODO: pass by reference
    mkfunc('mycsinf', sinname, ltypes.l_complex64)
    mkfunc('mycsin',  sinname, ltypes.l_complex128)
    mkfunc('mycsinl', sinname, ltypes.l_complex256)

    # print(ctx.module)
    ctx.link()
    print(ctx.module)

    m = test_support.make_mod(ctx)
    input = 10+2j

    result = cmath.sin(input)
    call = test_support.call_complex_byref

    r1 = call(m.mycsinf, input)
    r2 = call(m.mycsin,  input)
    r3 = call(m.mycsinl, input)

    print("expect:", result)
    print("got:", r1, r2, r3)
    assert np.allclose([result] * 3, [r1, r2, r3])

# ______________________________________________________________________

def test_link_binary():
    ctx = new_ctx()
    ty = ltypes.l_complex128
    make_func(ctx, 'mypow', powname + str(ty), ty, nargs=2)
    ctx.link()
    m = test_support.make_mod(ctx)

    inputs = 2+2j, 3+3j
    result = test_support.call_complex_byval(m.mypow, *inputs)
    expect = pow(*inputs)

    print(result, expect)
    assert result == expect, (result, expect)

# ______________________________________________________________________

def test_link_external():
    ctx = new_ctx()

test_link_real()
test_link_complex()