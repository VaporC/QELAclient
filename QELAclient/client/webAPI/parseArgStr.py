# import json
from inspect import signature, _empty
from typing import Callable
import json
from csv import reader as csvreader


TYPE_ALIASES = {'file': bytes, '"OK"/error': str, 'html': str}


def applyTyp(val: str, typ: type) -> object:
    # execute val=typ(val)
    #     print(val, typ, 8888888, val == b'True', TYPE_ALIASES.get(typ, typ))
    typ = TYPE_ALIASES.get(typ, typ)
    if typ is bytes:
        return val
    if typ is bool:
        #         if isinstance(val, str):
            # bool(s) where with len() >0 always returns True, therefore:
        return val == b'True'
    elif typ is str:
        if type(val) in (bytes, bytearray):
            val = val.decode()
        # remove trailing '":
        if len(val) and (val[0] == '"' and val[-1] == '"' or
                         val[0] == "'" and val[-1] == "'"):
            val = val[1:-1]
        return val
    elif typ == 'json':
        return json.loads(val)
    elif typ == 'csv':
        if type(val) is bytes:
            val = val.decode()
        if len(val) == 1:
            return []  # val is empty
        out = list(csvreader(val.split('\n')))
        if len(out) == 1:
            out = out[0]
        return out
    return typ(val)


def _formatArgs(fn: Callable, args: list, kwargs: dict) -> (list, dict):
    # set dtype of args, kwargs to dtype using in type hints of function,
    # if given
    sig = signature(fn)
    for i, p in enumerate(sig.parameters.values()):
        if i < len(args):
            typ = p.annotation
            # if dtype is given:
            if typ is not _empty:
                args[i] = applyTyp(args[i], typ)
        else:
            if p.default is not _empty:
                typ = type(p.default)
                if typ is not None:
                    try:
                        # change ftype, if kwarg exists:
                        kwargs[p.name] = applyTyp(kwargs[p.name], typ)
                    except KeyError:
                        pass

#     print(333, sig, fn, args, kwargs)


def parseArgStr(fn: Callable, s: str)->(list, dict):
    '''
    parse string [s] containing *args and **kwargs and
    set dtype corresponding to [fn]s signature
    '''
    nargs = fn.__code__.co_argcount
    if type(fn).__name__ == 'method':
        # remove <self> from number of
        # arguments:
        nargs -= 1
    if nargs == 0 or s is None:
        return (), {}
    elif nargs == 1:
        # dont split command
        args, kwargs = [s], {}
    else:
        args, kwargs = _parse(s, nargs)
#     except Exception:
#         args, kwargs = _parseJson(s)
    _formatArgs(fn, args, kwargs)
    return args, kwargs

# TODO: speed up code
# import cython
# @cython.compile


def _split(s: str, nargs: int)->list:
    # split s into pieces using , separator
    # ignore commas within (), {}, '', ""
    b0 = 0  # (
    b1 = 0  # {
    b2 = False  # '
    b3 = False  # "
    pos = []  # comma positions

    for i, e in enumerate(s):
        if e == ',':
            if not b0 and not b1 and not b2 and not b3:
                pos.append(i)
                if len(pos) == nargs:
                    # dont continue splitting the string if already number of
                    # fn args is reached
                    break
        else:
            if b0 + b1 == 0:
                # item is string
                if e == "'":
                    b2 = not b2
                elif e == '"':
                    b3 = not b3
                elif e == '"':
                    b3 += 1
            if b2 + b3 == 0:
                # item is bracket
                if e == "(":
                    b0 += 1
                elif e == "{":
                    b1 += 1
                elif e == ")":
                    b0 -= 1
                elif e == "}":
                    b1 -= 1
    pos.append(None)
    # do split:
    pieces = []
    p0 = -1
    for p1 in pos:
        pieces.append(s[p0 + 1:p1])
        p0 = p1
    return pieces


def _parse(s: str, nargs: int)->(list, dict):
    # a rather simple way
    args, kwargs = [], {}

    pieces = _split(s, nargs)

    for vi in pieces:  # TODO: ignore <,> in strings
        vi = vi.lstrip().rstrip()  # -> remove left/right whitespaces
        if '=' in vi:
            splitted = vi.split('=')  # ... kwargs are x=y
            key = splitted[0]
            # in case there is an <=> within the kwarg value
            val = '='.join(splitted[1:])
            kwargs[key.rstrip()] = val.lstrip()
        else:
            args.append(vi)
    return args, kwargs


if __name__ == '__main__':
    from time import time

    def fn(a1: str, a2: bool, a3: float, a4, kw1='aa', kw2=True):
        pass

    tests = [('kk,False,5,kw1=765,kw2=False',
              ['kk', False, 5.0], {'kw1': '765', 'kw2': False}),
             ('(ab"c,d), True, 5.1, kw1= "A(A,A", kw2 = False',
              ['(ab"c,d)', True, 5.1], {'kw1': "A(A,A", 'kw2': False}),
             #              'abcd, False, 5, kw1=(1,2,3), kw2=False',
             #              "True, 4, 6,  ddd=22, cc=jhg, dd=5,aaaaaa=8",
             #              '''1,2,3,{"a":4}'''
             ]
    t0 = time()

    for tstr, targs, tkwargs in tests:
        print('>> IN: %s' % tstr)
        args, kwargs = parseArgStr(fn, tstr)
        print('args')
        for a in args:
            print('\t', a, type(a))
        print('kwargs')
        for k, v in kwargs.items():
            print('\t%s: %s %s' % (k, v, type(v)))
        print("\n")

        assert targs == args
        assert tkwargs == kwargs
    t1 = time()
    print('execution time [s]: %.16f' % (t1 - t0))
