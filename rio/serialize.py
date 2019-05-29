import abc

try:
    import cPickle as pickle
except ImportError:
    import pickle

from typing import *


T = TypeVar('T')


class BaseSerializer(Generic[T]):
    """
    The serializer is responsible for converting complex python data types
    into primitive types that can be sent over zmq ports via msgpack.
    """
    # Used within the `MultiSerializer` to embed which serializer to use for
    # round-trip data serialization.
    signature = None  # type: str

    @abc.abstractmethod
    def serialize(self, data):
        """
        Serialize a python object to transport over zmq.

        Parameters
        ----------
        data : T

        Returns
        -------
        Any
        """
        raise NotImplementedError

    @abc.abstractmethod
    def deserialize(self, data):
        """
        Deserialize a python object. Counter of `serialize`.

        Parameters
        ----------
        data : Any

        Returns
        -------
        T
        """
        return NotImplementedError


class MultiSerializer(BaseSerializer):
    """
    Serializer with multple sub-serializers that can register methods to claim
    certain python objects.

    All serialized objects (besides list, tuples, sets, dicts) are represented
    as a tuple of (serializer.signature, serialized_value). This is so data
    can be properly decoded on the remote side.

    Register new sub-serializers using the register decorator:

        @MultiSerializer.register(lamba x: isinstance(x, MyCls))
        class MyClsSerializer(BaseSerializer):
            ...
    """

    _registered = []

    @classmethod
    def register(cls, claim_func):
        """
        Decorator for registering a callable to serialize certain types.

        Parameters
        ----------
        claim_func : Callable[Any, bool]

        Returns
        -------
        Callable[[T], T]
        """
        def _deco(serializer):
            cls._registered.insert(0, (claim_func, serializer))
            return serializer
        return _deco

    def __init__(self):
        self._serializers = {}  # type: Dict[str, BaseSerializer]
        self._claims = []  # type: List[Tuple[str, Callable[[Any], bool]]]
        for claim_func, serializerCls in self._registered:
            assert serializerCls.signature is not None, \
                'Populate the serializer.signature attribute.'
            assert serializerCls.signature not in self._serializers, \
                'Existing serializer with signature ' \
                '{!r}'.format(serializerCls.signature)
            serializer = serializerCls()
            self._claims.append((serializerCls.signature, claim_func))
            self._serializers[serializerCls.signature] = serializer

    def serialize(self, data):
        if isinstance(data, (list, tuple, set)):
            return type(data)(self.serialize(x) for x in data)
        elif isinstance(data, MutableMapping):
            return type(data)({self.serialize(k): self.serialize(v)
                               for k, v in data.items()})
        for name, claim_func in self._claims:
            if claim_func(data):
                return name, self._serializers[name].serialize(data)
        raise ValueError('No serializer found for {!r}'.format(data))

    def deserialize(self, payload):
        if not payload:
            return payload
        if isinstance(payload, (tuple, list)) \
                and len(payload) == 2 \
                and payload[0] in self._serializers.keys():
            signature, data = payload
            if signature not in self._serializers:
                raise ValueError('No deserializer found for {!r}'.format(data))
            return self._serializers[signature].deserialize(data)
        if isinstance(payload, (list, tuple, set)):
            return type(payload)(self.deserialize(x) for x in payload)
        elif isinstance(payload, MutableMapping):
            return type(payload)({self.deserialize(k): self.deserialize(v)
                                  for k, v in payload.items()})
        else:
            raise NotImplementedError


@MultiSerializer.register(lambda x: True)
class PickleSerializer(BaseSerializer):
    """
    Pickle serialization of python objects over the zmq ports.
    """
    signature = '_p'

    def serialize(self, data):
        return pickle.dumps(data, -1)

    def deserialize(self, data):
        return pickle.loads(data)


@MultiSerializer.register(lambda x: isinstance(x, Exception))
class ExceptionSerializer(BaseSerializer):
    """
    Exception serialization.
    """
    signature = '_e'

    def serialize(self, data):
        return pickle.dumps(data, -1)

    def deserialize(self, data):
        return pickle.loads(data)


@MultiSerializer.register(
    lambda x: isinstance(x, (str, unicode, bytes, int, float)))
class BasicSerializer(BaseSerializer):
    """
    Basic serialization of simple python types.
    """
    signature = '_b'

    def serialize(self, data):
        return data

    def deserialize(self, data):
        return data


class Encoder(object):
    """
    Handles how args and kwargs are encoded over zmq ports.

    By default zerorpc does not support passing kwargs to remote methods.
    This class is used to fix that so args are kwargs are combined into a
    single args payload that is then deconstructed on the remote side.
    """
    _default_serializer = PickleSerializer

    def __init__(self, serializer=None):
        if serializer is None:
            serializer = self._default_serializer()
        self.serializer = serializer

    def encode(self, *args, **kwargs):
        """
        Encode args and kwargs as a single serialized payload.

        Parameters
        ----------
        args : *Any
        kwargs : **Any

        Returns
        -------
        Tuple[Tuple[Any, ...], Dict[Any, Any]]
        """
        return self.serializer.serialize(args), \
               self.serializer.serialize(kwargs)

    def decode(self, *payload):
        """
        Decode encoded args and kwargs.

        Parameters
        ----------
        payload : Tuple[Tuple[Any, ...], Dict[Any, Any]]

        Returns
        -------
        Tuple[Tuple[Any, ...], Dict[Any, Any]]
        """
        if not payload:
            return (), {}
        args, kwargs = payload
        return self.serializer.deserialize(args), \
               self.serializer.deserialize(kwargs)
