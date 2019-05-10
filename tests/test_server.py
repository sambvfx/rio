import pytest

from rio.pipes import Server, Schema, _deserialize, _encode

import mymodule


@pytest.fixture
def server():
    return Server({
        'CONST': mymodule.CONST,
        'a': mymodule.a,
        'b': mymodule.b,
        'path': mymodule.path,
        'CustomPath.exists': mymodule.CustomPath.exists,
    })


def test_schema(server):
    assert server._schema['CONST'] == Schema.VALUE
    assert server._schema['a'] == Schema.CALLABLE
    assert server._schema['b'] == Schema.CALLABLE
    assert server._schema['path'] == Schema.MODULE
    assert server._schema['CustomPath.exists'] == Schema.CALLABLE


def test_callables(server):
    assert 'a' in server._methods
    assert _deserialize(server._methods['a']()) == 1


def test_values(server):
    assert 'CONST' in server._methods
    assert _deserialize(server._methods['CONST']()) == mymodule.CONST


def test_callable_args(server):
    assert 'b' in server._methods
    args = ('foo',)
    kwargs = {'bar': 'spangle'}
    payload = _encode(*args, **kwargs)
    rargs, rkwargs = _deserialize(server._methods['b'](*payload))
    assert rargs == args
    assert rkwargs == kwargs
