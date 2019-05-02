from __future__ import absolute_import, division, print_function

import sys
import inspect
import functools
import copy

import zerorpc

from kids.cache import undecorate, cache

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from typing import ModuleType
except ImportError:
    ModuleType = type(sys)


def _serialize(data):
    return pickle.dumps(data, -1)


def _deserialize(data):
    return pickle.loads(data)


def _encode(*args, **kwargs):
    return (_serialize({'args': args, 'kwargs': kwargs}),)


def _decode(*args):
    if not args:
        return (), {}
    data = _deserialize(args[0])
    return data['args'], data['kwargs']


def _serialization_wrapper(func):

    if not callable(func):
        result = copy.copy(func)
        func = lambda: result

    wrapper, wrapped = undecorate(func)

    @functools.wraps(wrapped)
    def wrap(*args):
        args, kwargs = _decode(*args)
        return _serialize(wrapped(*args, **kwargs))

    @functools.wraps(wrapped)
    def iterwrap(*args):
        args, kwargs = _decode(*args)
        for x in wrapped(*args, **kwargs):
            yield _serialize(x)

    if inspect.isgeneratorfunction(wrapped):
        return zerorpc.stream(wrapper(iterwrap))
    else:
        return zerorpc.rep(wrapper(wrap))


def iter_find_methods(obj, prefix=None, recursive=True):

    # FIXME: This is probably really broken and only works for because of
    #  __all__ check.

    _all = getattr(obj, '__all__', None)
    if _all is None:
        _all = dir(obj)

    for k in _all:

        if k.startswith('_'):
            continue

        if prefix is not None:
            key = '{}.{}'.format(prefix, k)
        else:
            key = k

        item = getattr(obj, k)

        yield key, item

        if recursive:
            if isinstance(item, ModuleType):
                for x in iter_find_methods(item, prefix=key):
                    yield x


class Schema:
    """
    Schema enum used for type information about RPC methods.
    """

    CALLABLE = 'CallableT'
    MODULE = 'ModuleTypeT'
    VALUE = 'AnyT'

    @classmethod
    def get(cls, obj):
        if callable(obj):
            return cls.CALLABLE
        if isinstance(obj, ModuleType):
            return cls.MODULE
        return cls.VALUE


class proxymodule(object):
    """
    Represents a remote module object.
    """

    def __init__(self, client, name):
        """
        Parameters
        ----------
        client : Client
        name : str
        """
        self._client = client
        self._name = name

    @property
    def _fullname(self):
        return '{}.{}'.format(self._client._name, self._name)

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self._fullname)

    def __getattr__(self, item):
        return getattr(self._client, '{}.{}'.format(self._name, item))


class Server(zerorpc.Server):

    def __init__(self, methods=None, name=None, context=None, pool_size=None,
                 heartbeat=5):

        if methods is None:
            methods = self

        if not isinstance(methods, dict):
            methods = dict(iter_find_methods(methods))

        _methods = self._filter_methods(Server, self, methods)
        # Do this before wrapping with serialization / decorators
        self._schema = {k: Schema.get(v) for k, v in _methods.items()}
        _methods = {k: _serialization_wrapper(v) for k, v in _methods.items()
                    if not isinstance(v, ModuleType)}

        super(Server, self).__init__(
            methods=_methods, name=name, context=context, pool_size=pool_size,
            heartbeat=heartbeat)

    def _inject_builtins(self):
        super(Server, self)._inject_builtins()
        self._methods['_schema'] = lambda: self._schema


class Client(zerorpc.Client):

    def __init__(self, connect_to=None, context=None, timeout=30, heartbeat=5,
                 passive_heartbeat=False, prefix=None):
        super(Client, self).__init__(
            connect_to=connect_to, context=context, timeout=timeout,
            heartbeat=heartbeat, passive_heartbeat=passive_heartbeat)

        self._prefix = prefix

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self):
        return '<{}.{}({!r})>'.format(
            self.__module__, self.__class__.__name__, self._name)

    @cache
    @property
    def _name(self):
        return str(self('_zerorpc_name'))

    @cache
    @property
    def _schema(self):
        return self('_schema')

    @cache
    @property
    def _methods(self):
        return self('_zerorpc_list')

    def _nonserialized_call(self, method, *args, **kwargs):
        return super(Client, self).__call__(method, *args, **kwargs)

    def _serialized_call(self, method, *args, **kwargs):
        kw = {}
        for k in ('timeout', 'slotes', 'async'):
            try:
                kw[k] = kwargs.pop(k)
            except KeyError:
                pass

        if args or kwargs:
            payload = _encode(*args, **kwargs)
        else:
            payload = ()

        return _deserialize(
            super(Client, self).__call__(method, *payload, **kw))

    def __call__(self, method, *args, **kwargs):
        # Private methods we don't bother serializing since they take extra
        # work to serve so we assume they're sending perfectly safe types.
        if method.startswith('_'):
            return self._nonserialized_call(method, *args, **kwargs)
        return self._serialized_call(method, *args, **kwargs)

    def __getattr__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            pass

        if self._prefix is not None:
            method = '{}.{}'.format(self._prefix, item)
        else:
            method = item

        # # IPython fix
        # if method in ('trait_names', '_getAttributeNames'):
        #     return self._methods

        schema = self._schema.get(method)

        if schema == Schema.VALUE:
            # FIXME: I'm passing the method name as part of the arg call.
            #  There were issues storing `lambda: getattr(mod, k)` as the method
            #  and it returned *different items from the module*. Need to
            #  understand what's happening.
            return self(method, item)

        elif schema == Schema.MODULE:
            # Return our proxymodule shim object.
            return proxymodule(self, item)

        # Ensure method is valid.
        if method not in self._methods:
            raise AttributeError('{!r} has no attribute {!r}'.format(
                self._name, method))

        return lambda *args, **kargs: self(method, *args, **kargs)
