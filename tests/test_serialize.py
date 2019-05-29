import pytest

from rio.serialize import Encoder, BaseSerializer, BasicSerializer, \
    PickleSerializer, MultiSerializer

import mymodule


@MultiSerializer.register(lambda x: isinstance(x, mymodule.CustomPath))
class MyPathSerializer(BaseSerializer):
    signature = 'CustomPath'

    def serialize(self, data):
        return str(data)

    def deserialize(self, data):
        return mymodule.CustomPath(data)


@pytest.fixture(params=[BasicSerializer, PickleSerializer, MultiSerializer])
def serializer(request):
    return request.param()


def test_encoder(serializer):
    encoder = Encoder(serializer)
    args = ('arg1', 42)
    kwargs = dict(kw1='kw1', kw2=3.14)
    encoded = encoder.encode(*args, **kwargs)
    assert len(encoded) == 2
    decoded = encoder.decode(*encoded)
    assert (args, kwargs) == decoded


def test_multiserialier():
    encoder = Encoder(MultiSerializer())

    assert isinstance(encoder.serializer, MultiSerializer)

    assert MyPathSerializer.signature in encoder.serializer._serializers.keys()
    assert any(isinstance(x, MyPathSerializer) for x in
               encoder.serializer._serializers.values())
    assert MyPathSerializer.signature in [x[0] for x in
                                          encoder.serializer._claims]


def test_custom_multiserializer():
    encoder = Encoder(MultiSerializer())
    args = (mymodule.CustomPath('/foo'),)
    kwargs = {}
    encoded = encoder.encode(*args, **kwargs)
    assert len(encoded) == 2
    assert encoded == ((('CustomPath', '/foo'),), {})
    decoded = encoder.decode(*encoded)
    assert (args, kwargs) == decoded


def test_nested_multiserializer():
    encoder = Encoder(MultiSerializer())

    args = (
        'foo',
        mymodule.CustomPath('/foo'),
        42,
    )
    kwargs = dict(
        bar='value',
        barpath=mymodule.CustomPath('/bar')
    )
    encoded = encoder.encode(*args, **kwargs)
    assert len(encoded) == 2
    assert encoded == (
        (
            ('_b', 'foo'),
            ('CustomPath', '/foo'),
            ('_b', 42)
        ),
        {
            ('_b', 'bar'): ('_b', 'value'),
            ('_b', 'barpath'): ('CustomPath', '/bar')
        }
    )
    decoded = encoder.decode(*encoded)
    assert (args, kwargs) == decoded
