"""
Client tests.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import functools
import subprocess
import pathlib

import pytest

from rio.rpc import rio, iterfsmethods
from rio.pipes import Server

import mymodule


SERVER_SOCKET = 'tcp://0.0.0.0:4242'
CLIENT_SOCKET = 'tcp://127.0.0.1:4242'

TEST_PATH_EXISTS = '/tmp/rio_tests'
TEST_CHILDPATH = '/tmp/rio_tests/child'
TEST_PATH_NOT_EXISTS = '/tmp/rio_tests_not'


def switcharoo(func, name=None):

    if not callable(func):
        return func

    if name is None:
        name = func.__name__

    @functools.wraps(func)
    def _wrap(*args, **kwargs):

        if args:
            args = list(args)
            path = args[0]
            path = type(path)(TEST_PATH_EXISTS)
            args = tuple([path] + args[1:])

        # s = '{}('.format(name)
        # if args:
        #     s += ', '.join(repr(x) for x in args)
        # if kwargs:
        #     s += ', '.join('{}={!r}'.format(k, v) for k, v in kwargs.items())
        # s += ')'
        # print(s)

        return func(*args, **kwargs)

    return _wrap


def start_server():
    methods = {k: switcharoo(v, name=k) for k, v in iterfsmethods()}
    s = Server(methods=methods)
    s.bind(SERVER_SOCKET)
    print('starting rio server')
    s.run()


if __name__ == '__main__':
    start_server()


@pytest.fixture
def path():
    return TEST_PATH_NOT_EXISTS


@pytest.fixture
def pathlibpath(path):
    return pathlib.Path(path)


@pytest.fixture
def custompath(path):
    return mymodule.CustomPath(path)


@pytest.fixture
def ctx():
    return rio(CLIENT_SOCKET)


class TestPath(object):

    server = None

    @classmethod
    def setup_class(cls):
        if os.path.exists(TEST_PATH_NOT_EXISTS):
            os.remove(TEST_PATH_NOT_EXISTS)

        if os.path.exists(TEST_PATH_EXISTS):
            os.remove(TEST_PATH_EXISTS)

        os.mkdir(TEST_PATH_EXISTS)
        with open(TEST_CHILDPATH, 'a'):
            os.utime(TEST_CHILDPATH, None)

        cls.server = subprocess.Popen(
            ['python', __file__],
        )

    @classmethod
    def teardown_class(cls):
        cls.server.kill()
        os.remove(TEST_CHILDPATH)
        os.rmdir(TEST_PATH_EXISTS)

    @staticmethod
    def test_os_local(path):
        assert not os.path.exists(path)
        with pytest.raises(OSError):
            os.stat(path)

    @staticmethod
    def test_os_patched(ctx):
        with ctx as r:
            patched = [t[0] for t in r._ctxs]
            assert 'os.path.exists' in patched
            assert 'os.stat' in patched

    @staticmethod
    def test_os_rpc(path, ctx):
        with ctx:
            assert os.path.exists(path)
            assert os.stat(path)

    @staticmethod
    def test_pathlib_local(pathlibpath):
        assert not pathlibpath.exists()
        with pytest.raises(OSError):
            pathlibpath.stat()

    @staticmethod
    def test_pathlib_patched(ctx):
        with ctx as r:
            patched = [x[0] for x in r._ctxs]
            assert 'pathlib._NormalAccessor.stat' in patched

    @staticmethod
    def test_pathlib_rpc(pathlibpath, ctx):
        with ctx:
            assert pathlibpath.exists()
            assert pathlibpath.stat()

    @staticmethod
    def test_custom_local(custompath):
        assert not custompath.exists()
        with pytest.raises(OSError):
            custompath.stat()

    @staticmethod
    def test_custom_rpc(custompath, ctx):
        with ctx:
            assert custompath.exists()
            assert custompath.stat()

    @staticmethod
    def test_custom_local_listdir(custompath):
        assert not custompath.listdir()

    @staticmethod
    def test_custom_rpc_listdir(custompath, ctx):
        expected = [mymodule.CustomPath(TEST_CHILDPATH)]
        with ctx:
            assert expected == custompath.listdir()
