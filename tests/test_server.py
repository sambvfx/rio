import pytest

from rio.pipes import Server, Schema, _deserialize

import _testmodule


@pytest.fixture
def server():
    return Server(_testmodule)


def test_server_schema(server):
    assert server._schema['CONST'] == Schema.VALUE
    assert server._schema['a'] == Schema.CALLABLE
    assert server._schema['b'] == Schema.CALLABLE
    assert server._schema['path'] == Schema.MODULE


def test_server_methods(server):
    assert 'a' in server._methods
    assert 'b' in server._methods


def test_server_method_values(server):
    assert 'CONST' in server._methods
    assert _deserialize(server._methods['CONST']()) == _testmodule.CONST
