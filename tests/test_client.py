"""
Client tests.
"""
import os

import functools
import gevent
import pathlib

import pytest

import rio.server
import rio.api
from rio.collections.fs import iterfsmethods
from rio.pipes import ProxyModule

import mymodule


SERVER_SOCKET = 'tcp://0.0.0.0:4242'
CLIENT_SOCKET = 'tcp://127.0.0.1:4242'


def healthcheck(greenlet):
    if greenlet.dead:
        if getattr(greenlet, 'exception', None) is not None:
            if hasattr(greenlet, '_raise_exception'):
                greenlet._raise_exception()
            else:
                raise greenlet.exception


@pytest.fixture
def client():
    return rio.api.rio(CLIENT_SOCKET, timeout=1.0)


class TestSchema(object):
    """
    Collection of schema-type tests.
    """

    server = None

    @classmethod
    def setup_class(cls):
        cls.server = gevent.spawn(rio.server.start, mymodule)
        gevent.sleep(0.5)
        healthcheck(cls.server)

    @classmethod
    def setup_method(cls):
        healthcheck(cls.server)

    @classmethod
    def teardown_class(cls):
        cls.server.kill()
        cls.server = None

    @staticmethod
    def test_getattr_callable(client):
        assert callable(getattr(client, 'tests.mymodule.a'))

    @staticmethod
    def test_getattr_value(client):
        assert getattr(client, 'tests.mymodule.CONST') == 42

    @staticmethod
    def test_getattr_module(client):
        assert isinstance(getattr(client, 'tests.mymodule.path'), ProxyModule)

    @staticmethod
    def test_raise_error(client):
        with client:
            with pytest.raises(ValueError):
                mymodule.raise_error()


TEST_PATH_EXISTS = '/tmp/rio_tests'
TEST_CHILDPATH = '/tmp/rio_tests/child'
TEST_PATH_NOT_EXISTS = '/tmp/rio_tests_not'


def switcharoo(func):

    if not callable(func):
        return func

    @functools.wraps(func)
    def _wrap(*args, **kwargs):

        if args:
            args = list(args)
            path = args[0]
            path = type(path)(TEST_PATH_EXISTS)
            args = tuple([path] + args[1:])

        return func(*args, **kwargs)

    return _wrap


@pytest.fixture
def path():
    return TEST_PATH_NOT_EXISTS


@pytest.fixture
def pathlibpath(path):
    return pathlib.Path(path)


@pytest.fixture
def custompath(path):
    return mymodule.CustomPath(path)


class TestFS(object):
    """
    Collection of file system tests.

    This works by "switching" the requested path to one that exists (so we
    know the rpc call worked).
    """

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

        cls.server = gevent.spawn(
            rio.server.start,
            {k: switcharoo(v) for k, v in iterfsmethods()})

        gevent.sleep(0.5)
        healthcheck(cls.server)

    @classmethod
    def setup_method(cls):
        healthcheck(cls.server)

    @classmethod
    def teardown_class(cls):
        cls.server.kill()
        cls.server = None
        cls._cleanup()

    @staticmethod
    def test_os_local(path):
        assert not os.path.exists(path)
        with pytest.raises(OSError):
            os.stat(path)

    @staticmethod
    def test_os_rpc(path, client):
        with client:
            assert os.path.exists(path)
            assert os.stat(path)

    @staticmethod
    def test_pathlib_local(pathlibpath):
        assert not pathlibpath.exists()
        with pytest.raises(OSError):
            pathlibpath.stat()

    @staticmethod
    def test_pathlib_rpc(pathlibpath, client):
        with client:
            assert pathlibpath.exists()
            assert pathlibpath.stat()

    @staticmethod
    def test_custom_local(custompath):
        assert not custompath.exists()
        with pytest.raises(OSError):
            custompath.stat()

    @staticmethod
    def test_custom_rpc(custompath, client):
        with client:
            assert custompath.exists()
            assert custompath.stat()

    @staticmethod
    def test_custom_local_listdir(custompath):
        assert not custompath.listdir()

    @staticmethod
    def test_custom_rpc_listdir(custompath, client):
        with client:
            assert custompath.listdir()

    @staticmethod
    def test_client(client):
        assert 'open' in client._methods
