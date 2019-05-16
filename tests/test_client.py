"""
Client tests.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import functools
import subprocess
import pathlib

import pytest

from rio.api import rio
from rio.packages.fs import iterfsmethods
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
    try:
        # Because we're changing the path, we need to run the os.path.join
        # (part of listdir) remotely. Override the default excludes so all
        # os.path commands run remote.
        methods = {k: switcharoo(v, name=k) for k, v in iterfsmethods(
            excludes=None)}
        s = Server(methods=methods)
        s.bind(SERVER_SOCKET)
        print('starting rio server')
        s.run()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


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

    @staticmethod
    def _cleanup():
        if os.path.exists(TEST_PATH_NOT_EXISTS):
            os.remove(TEST_PATH_NOT_EXISTS)

        if os.path.exists(TEST_CHILDPATH):
            os.remove(TEST_CHILDPATH)

        if os.path.exists(TEST_PATH_EXISTS):
            os.rmdir(TEST_PATH_EXISTS)

    @classmethod
    def setup_class(cls):
        cls._cleanup()

        os.mkdir(TEST_PATH_EXISTS)
        with open(TEST_CHILDPATH, 'a'):
            os.utime(TEST_CHILDPATH, None)

        cls.server = subprocess.Popen(
            ['python', __file__],
        )
        time.sleep(1.0)
        cls.server.poll()
        if cls.server.returncode is not None:
            raise RuntimeError('Server subprocess failed to start properly')

    @classmethod
    def teardown_class(cls):
        cls.server.kill()
        cls._cleanup()

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
