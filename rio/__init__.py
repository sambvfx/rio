from __future__ import absolute_import, print_function

import sys

from collections import defaultdict
import functools

import mock

from .pipes import Client


_PATCH_EXCLUDE_MODULES = frozenset((
    'unittest',
    'pytest',
    '_pytest',
    'py',
    'pluggy',
))


def _multiio(clients, func_name, *args, **kwargs):
    results = []
    for client in clients:
        results.append(client(func_name, *args, **kwargs))
    if len(results) == 1:
        return results[0]
    return tuple(results)


class RIO(object):

    def __init__(self, *targets):
        self._ctxs = []  # List[Callable]
        self._targets = targets  # List[str]

    def iter_patched(self):

        methods = defaultdict(list)
        for target in self._targets:
            c = Client(connect_to=target, timeout=5.0)
            for m in c._methods:
                methods[m].append(c)

        seen = set()

        for func_name, clients in methods.items():

            func = functools.partial(_multiio, clients, func_name)

            yield mock.patch(func_name, side_effect=func)

            parts = func_name.split('.')
            for k, mod in sys.modules.items():
                if any(k.startswith(s) for s in _PATCH_EXCLUDE_MODULES):
                    continue
                path = [k]
                for part in parts:
                    mod = getattr(mod, part, None)
                    if mod is None:
                        break
                    else:
                        path.append(part)
                else:
                    key = '.'.join(path)
                    if key in seen:
                        continue
                    seen.add(key)

                    yield mock.patch(key, side_effect=func)

    def __enter__(self):
        for ctx in self.iter_patched():
            ctx.__enter__()
            self._ctxs.append(ctx)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctxs:
            for ctx in reversed(self._ctxs):
                ctx.__exit__()
        self._ctxs = []


def test():
    """
    Tests to be executed with a server started.
    """

    # os

    import os

    path = '/tmp/os'

    print('\n\n')
    print('-'*80)
    print('Testing os')
    print()

    print('>>> os.path.exists({!r})'.format(path), os.path.exists(path))
    try:
        r = os.stat(path).st_size
    except Exception as e:
        r = e
    print('>>> os.stat({!r}).st_size'.format(path), r)
    print()
    print('>>> with RIO(\'tcp://127.0.0.1:4242\'):')
    with RIO('tcp://127.0.0.1:4242'):
        print('...     os.path.exists({!r})'.format(path), os.path.exists(path))
        try:
            r = os.stat(path).st_size
        except Exception as e:
            r = e
        print('...     os.stat({!r}).st_size'.format(path), r)

    # pathlib

    import pathlib

    p = pathlib.Path('/tmp/pathlib')

    print('\n\n')
    print('-'*80)
    print('Testing pathlib')
    print()

    print('>>> {!r}.exists()'.format(p), p.exists())
    try:
        r = p.stat().st_size
    except Exception as e:
        r = e
    print('>>> {!r}.stat().st_size'.format(p), r)
    print()
    print('>>> with RIO(\'tcp://127.0.0.1:4242\'):')
    with RIO('tcp://127.0.0.1:4242'):
        print('...     {!r}.exists()'.format(p), p.exists())
        try:
            r = p.stat().st_size
        except Exception as e:
            r = e
        print('...     {!r}.stat().st_size'.format(p), r)

    # custom

    class CustomPath(object):

        existsmeth = staticmethod(os.path.exists)
        statsmeth = staticmethod(os.stat)

        def __init__(self, p):
            self._path = p

        def __repr__(self):
            return '{}({!r})'.format(self.__class__.__name__, str(self._path))

        def __str__(self):
            return str(self._path)

        def exists(self):
            return self.existsmeth(str(self))

        def stat(self):
            return self.statsmeth(str(self))

    p = CustomPath('/tmp/mypath')

    print('\n\n')
    print('-'*80)
    print('Testing custom')
    print()

    print('>>> {!r}.exists()'.format(p), p.exists())
    try:
        r = p.stat().st_size
    except Exception as e:
        r = e
    print('>>> {!r}.stat().st_size'.format(p), r)
    print()
    print('>>> with RIO(\'tcp://127.0.0.1:4242\'):')
    with RIO('tcp://127.0.0.1:4242'):
        print('...     {!r}.exists()'.format(p), p.exists())
        try:
            r = p.stat().st_size
        except Exception as e:
            r = e
        print('...     {!r}.stat().st_size'.format(p), r)

    print('\n\n')
