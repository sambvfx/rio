from __future__ import absolute_import, print_function

import os
import functools

from .pipes import Server
from .log import get_logger


_logger = get_logger(__name__)


def _debug(func, name=None):
    """
    Wrap a method so it's logged when it's called.

    Parameters
    ----------
    func : Any
    name : Optional[str]

    Returns
    -------
    Any
    """
    if not callable(func):
        if name:
            _logger.debug(name)
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
        _logger.debug(s)
        return func(*args, **kwargs)

    return _wrap


def start(methods=None, host=None, port=None, debug=True):
    """
    Starts a rio server and blocks forever.

    Parameters
    ----------
    methods : Optional[Any]
        Passed into the zerorpc.Server.
    host : Optional[str]
    port : Optional[Union[int, str]]
    debug : bool
        Wraps all methods in another layer that prints commands that are
        executed.
    """
    if methods is None:
        from .collections.fs import iterfsmethods
        methods = dict(iterfsmethods())

    if debug and isinstance(methods, dict):
        methods = {k: _debug(v, name=k) for k, v in methods.items()}

    if host is None:
        host = os.environ.get('RIO_HOST', '0.0.0.0')
    if port is None:
        port = os.environ.get('RIO_PORT', '4242')

    url = 'tcp://{}:{}'.format(host, port)

    s = Server(methods=methods, name='rio')

    s.bind(url)

    _logger.debug('starting server @ {}'.format(url))
    for k, v in sorted(s._methods.items()):
        _logger.debug('  {} ({})'.format(k, s._schema.get(k)))

    try:
        s.run()
    finally:
        s.close()
