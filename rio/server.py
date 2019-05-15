from __future__ import absolute_import, print_function

import functools

from .rpc import iterfsmethods
from .pipes import Server


def _debug(func, name=None):

    if not callable(func):
        return func

    if name is None:
        name = '{}.{}'.format(func.__module__, func.__name__)

    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        # args = ('/tmp',)
        s = '{}('.format(name)
        if args:
            s += ', '.join(repr(x) for x in args)
        if kwargs:
            s += ', '.join('{}={!r}'.format(k, v) for k, v in kwargs.items())
        s += ')'
        print(s)
        return func(*args, **kwargs)

    return _wrap


def start(url='tcp://0.0.0.0:4242', debug=True):
    methods = dict(iterfsmethods())

    if debug:
        methods = {k: _debug(v, name=k) for k, v in methods.items()}

    s = Server(methods=methods, name='rio')

    s.bind(url)

    print('starting server @ tcp://0.0.0.0:4242')
    for k, v in sorted(s._methods.items()):
        print('  {} ({})'.format(k, s._schema.get(k)))

    s.run()
