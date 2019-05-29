import pytest

from rio.pipes import Server, Schema
from rio.serialize import Encoder

import mymodule


@pytest.fixture
def methodserver():
    return Server({
        'CONST': mymodule.CONST,
        'a': mymodule.a,
        'b': mymodule.b,
        'path': mymodule.path,
        'CustomPath.exists': mymodule.CustomPath.exists,
    })


@pytest.fixture
def pathserver():
    return Server(mymodule.CustomPath('/tmp'))


@pytest.fixture
def moduleserver():
    return Server(mymodule)


@pytest.fixture
def encoder():
    return Encoder()


def test_schema(methodserver):
    schema = methodserver._schema
    assert schema['CONST'] == Schema.VALUE
    assert schema['a'] == Schema.CALLABLE
    assert schema['b'] == Schema.CALLABLE
    assert schema['path'] == Schema.MODULE
    assert schema['CustomPath.exists'] == Schema.CALLABLE


def test_callables(methodserver, encoder):
    assert 'a' in methodserver._methods
    assert encoder.serializer.deserialize(methodserver._methods['a']()) == 1


def test_values(methodserver, encoder):
    assert 'CONST' in methodserver._methods
    assert encoder.serializer.deserialize(
        methodserver._methods['CONST']()) == mymodule.CONST


def test_callable_args(methodserver, encoder):
    assert 'b' in methodserver._methods
    args = ('foo',)
    kwargs = {'bar': 'spangle'}
    payload = encoder.encode(*args, **kwargs)
    rargs, rkwargs = encoder.serializer.deserialize(
        methodserver._methods['b'](*payload))
    assert rargs == args
    assert rkwargs == kwargs


def test_schema_obj(pathserver):
    schema = pathserver._schema
    assert schema['tests.mymodule.CustomPath.exists'] == Schema.CALLABLE
    assert schema['tests.mymodule.CustomPath.stat'] == Schema.CALLABLE
    assert schema['tests.mymodule.CustomPath.parent'] == Schema.VALUE


def test_schema_module(moduleserver):
    schema = moduleserver._schema
    assert schema['tests.mymodule.CustomPath'] == Schema.CALLABLE
    assert schema['tests.mymodule.a'] == Schema.CALLABLE
    assert schema['tests.mymodule.CONST'] == Schema.VALUE
