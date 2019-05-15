from __future__ import absolute_import, print_function

import os

from collections import defaultdict
import functools
import pathlib

import mock

from .pipes import Client


# _PATCH_EXCLUDE_MODULES = frozenset((
#     'unittest',
#     'pytest',
#     '_pytest',
#     'py',
#     'pluggy',
# ))


def iterfsmethods():

    names = [s for s in dir(pathlib._NormalAccessor) if s[0] != '_']
    for name in names:
        obj = getattr(os, name, None)
        if obj is not None:
            yield 'os.{}'.format(name), obj

    for name in os.path.__all__:
        obj = getattr(os.path, name, None)
        if obj is not None:
            yield 'os.path.{}'.format(name), obj

    for name in names:
        obj = getattr(pathlib._NormalAccessor, name)
        yield 'pathlib._NormalAccessor.{}'.format(name), obj


def _multiio(clients, func_name, *args, **kwargs):
    # s = '{}('.format(func_name)
    # if args:
    #     s += ', '.join(repr(x) for x in args)
    # if kwargs:
    #     s += ', '.join('{}={!r}'.format(k, v) for k, v in kwargs.items())
    # s += ')'
    # print(s)
    results = []
    for client in clients:
        results.append(client(func_name, *args, **kwargs))
    if len(results) == 1:
        return results[0]
    return tuple(results)


class rio(object):

    def __init__(self, *targets):
        self._ctxs = []  # List[Tuple[str, mock._patch]]
        self._targets = targets  # Iterable[str]

    def __iter__(self):

        methods = defaultdict(list)
        for target in self._targets:
            c = Client(connect_to=target, timeout=5.0)
            for m in c._methods:
                methods[m].append(c)

        # seen = set()

        for func_name, clients in methods.items():

            func = functools.partial(_multiio, clients, func_name)

            # print('Patching {!r}'.format(func_name))
            yield func_name, mock.patch(
                func_name, autospec=True, side_effect=func)

            # parts = func_name.split('.')
            # for k, mod in sys.modules.items():
            #     if k == parts[0]:
            #         continue
            #     if any(k.startswith(s) for s in _PATCH_EXCLUDE_MODULES):
            #         continue
            #     path = [k]
            #     for part in parts:
            #         mod = getattr(mod, part, None)
            #         if mod is None:
            #             break
            #         else:
            #             path.append(part)
            #     else:
            #         key = '.'.join(path)
            #         if key in seen:
            #             continue
            #         seen.add(key)
            #         # print('  + {!r}'.format(key))
            #         yield key, mock.patch(key, side_effect=func)

    def __enter__(self):
        for name, ctx in iter(self):
            try:
                ctx.__enter__()
            except ImportError:
                pass
            self._ctxs.append((name, ctx))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctxs:
            for _, ctx in reversed(self._ctxs):
                ctx.__exit__()
        self._ctxs = []
