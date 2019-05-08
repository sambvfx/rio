from __future__ import absolute_import, print_function

import os
import functools

from .pipes import Server


def _debug(func, name=None):

    if name is None:
        name = '{}.{}'.format(func.__module__, func.__name__)

    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        args = ('/tmp',)
        print('{}(*{!r}, **{!r})'.format(name, args, kwargs))
        return func(*args, **kwargs)

    return _wrap


_FILESYSTEM_CALLS = {
    'os.stat': os.stat,
    'os.path.exists': os.path.exists,
}

try:
    import pathlib
except ImportError:
    pass
else:
    _FILESYSTEM_CALLS.update({
        'pathlib.Path.exists': lambda x: pathlib.Path(x).exists(),
        'pathlib.Path.stat': lambda x: pathlib.Path(x).stat(),
    })


def start(url='tcp://0.0.0.0:4242', debug=True):
    methods = _FILESYSTEM_CALLS
    if debug:
        methods = {k: _debug(v, name=k) for k, v in methods.items()}

    s = Server(methods=methods, name='rio')

    s.bind(url)

    print('starting server @ tcp://0.0.0.0:4242')
    for k, v in sorted(s._methods.items()):
        print('  {} ({})'.format(k, s._schema.get(k)))

    s.run()
