"""
Client tests.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import functools
import subprocess

import pytest

from rio import RIO
from rio.pipes import Server

import _testmodule


SERVER_SOCKET = 'tcp://0.0.0.0:4242'
CLIENT_SOCKET = 'tcp://127.0.0.1:4242'

TEST_PATH = '/tmp/rio_tests'


def switcharoo(func, name=None):

    if name is None:
        name = func.__name__

    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        if args:
            args = (TEST_PATH,)
        s = '{}('.format(name)
        if args:
            s += ', '.join(repr(x) for x in args)
        if kwargs:
            s += ', '.join('{}={!r}'.format(k, v) for k, v in kwargs.items())
        s += ')'
        print(s)

        return func(*args, **kwargs)

    return _wrap


def start_server():
    methods = {
        'os.path.exists': switcharoo(os.path.exists, 'os.path.exists'),
        'os.stat': switcharoo(os.stat, 'os.stat'),
        '_testmodule.CustomPath.existsmeth': switcharoo(os.path.exists, 'CustomPath.exists'),
        '_testmodule.CustomPath.statsmeth': switcharoo(os.stat, 'CustomPath.stat'),
    }
    try:
        import pathlib
    except ImportError:
        pass
    else:
        methods.update({
            'pathlib._NormalAccessor.stat': switcharoo(os.stat, 'pathlib.Path.stat'),
        })

    s = Server(methods)
    s.bind(SERVER_SOCKET)
    s.run()


if __name__ == '__main__':
    start_server()


class TestPath(object):

    server = None

    @classmethod
    def setup_class(cls):

        with open(TEST_PATH, 'a'):
            os.utime(TEST_PATH, None)

        cls.server = subprocess.Popen(['python', __file__])

    @classmethod
    def teardown_class(cls):
        cls.server.kill()
        os.remove(TEST_PATH)

    @staticmethod
    def test_os():
        path = '/tmp/os'

        assert not os.path.exists(path)
        with pytest.raises(OSError):
            os.stat(path)

        with RIO(CLIENT_SOCKET):
            assert os.path.exists(path)
            assert os.stat(path)

    @staticmethod
    def test_pathlib():
        import pathlib
        p = pathlib.Path('/tmp/pathlib')
        assert not p.exists()
        with pytest.raises(OSError):
            p.stat()

        with RIO(CLIENT_SOCKET):
            assert p.exists()
            assert p.stat()

    @pytest.mark.skip('Not working yet')
    @staticmethod
    def test_custom():

        p = _testmodule.CustomPath('/tmp/mypath')

        assert not p.exists()
        with pytest.raises(OSError):
            p.stat()

        with RIO(CLIENT_SOCKET):
            assert p.exists()
            assert p.stat()
