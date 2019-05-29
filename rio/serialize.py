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
        Callable[Any, Union[bytes, Iterator[bytes]]]
        """
        def _deco(serializer):
            cls._registered.insert(0, (claim_func, serializer))
            return serializer
        return _deco

    def __init__(self):
        self._serializers = {}  # type: Dict[str, BaseSerializer]
        self._claims = []  # type: List[Tuple[str, Callable[[Any], bool]]]
        for claim_func, serializerCls in self._registered:
            name = serializerCls.__name__
            serializer = serializerCls()
            self._claims.append((name, claim_func))
            self._serializers[name] = serializer

    def serialize(self, data):
        for name, claim_func in self._claims:
            if claim_func(data):
                return name, self._serializers[name].serialize(data)
        raise ValueError('No serializer found for {!r}'.format(data))

    def deserialize(self, data):
        name, payload = data
        if name not in self._serializers:
            raise ValueError('No deserializer found for {!r}'.format(data))
        return self._serializers[name].deserialize(payload)


@MultiSerializer.register(lambda x: True)
class PickleSerializer(BaseSerializer):
    """
    Pickle serialization of python objects over the zmq ports.
    """

    def serialize(self, data):
        return pickle.dumps(data, -1)

    def deserialize(self, data):
        return pickle.loads(data)


class Encoder(object):
    """
    Handles how args and kwargs are encoded over zmq ports.

    By default zerorpc does not support passing kwargs to remote methods.
    This class is used to fix that so args are kwargs are combined into a
    single args payload that is then deconstructed on the remote side.
    """

    def __init__(self, serializer=None):
        if serializer is None:
            serializer = MultiSerializer()
        self.serializer = serializer

    def encode(self, *args, **kwargs):
        if not args and not kwargs:
            return ()
        return tuple([self.serializer.serialize((args, kwargs))])

    def decode(self, *args):
        if not args:
            return (), {}
        return self.serializer.deserialize(args[0])
