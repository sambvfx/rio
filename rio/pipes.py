import sys
import inspect
import functools

import zerorpc

from kids.cache import undecorate, cache

from .serialize import Encoder

try:
    from typing import ModuleType
except ImportError:
    ModuleType = type(sys)


def _fetch(value):
    # passthrough used for wrapping non-methods
    return value


def _serialization_wrapper(func_or_value, encoder):
    """
    Wrap `func_or_value` to be used by zerorpc. This handles encoding/decoding
    args and kwargs and wrapping with the proper zerorpc decorator.

    Parameters
    ----------
    func_or_value : Any
        Typically a callable although this supports hosting constant values
        as well.
    encoder : Encoder
        Used to encode/decode args and kwargs.

    Returns
    -------
    zerorpc.decorators.DecoratorBase
    """

    if not callable(func_or_value):
        func_or_value = functools.partial(_fetch, func_or_value)
        func_or_value.__module__ = 'rio.virtual'
        func_or_value.__name__ = 'rio.virtual'

    wrapper, wrapped = undecorate(func_or_value)

    @functools.wraps(wrapped)
    def wrap(*args):
        args, kwargs = encoder.decode(*args)
        return encoder.serializer.serialize(wrapped(*args, **kwargs))

    @functools.wraps(wrapped)
    def iterwrap(*args):
        args, kwargs = encoder.decode(*args)
        for x in wrapped(*args, **kwargs):
            yield encoder.serializer.serialize(x)

    if inspect.isgeneratorfunction(wrapped):
        return zerorpc.stream(wrapper(iterwrap))
    else:
        return zerorpc.rep(wrapper(wrap))


class Schema(object):
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


class ProxyModule(object):
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
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            pass
        return getattr(self._client, '{}.{}'.format(self._name, item))


class Server(zerorpc.Server):
    """
    Modified zerorpc server that adds extended functionality.

    Features include:
      - All methods are wrapped in a serialization layer so any types of args
        and kwargs can be passed.
      - True first-class exceptions.
      - Keeps track of method "schema" which allows hosting of more than just
        callable methods (such as constants or even modules).
    """

    def __init__(self, methods=None, name=None, context=None, pool_size=None,
                 heartbeat=5, encoder=None):

        if encoder is None:
            encoder = Encoder()
        self.encoder = encoder

        if methods is None:
            methods = self

        _methods = self._filter_methods(Server, self, methods)
        # Do this before wrapping with serialization / decorators
        self._schema = {k: Schema.get(v) for k, v in _methods.items()}
        _methods = {k: _serialization_wrapper(v, self.encoder)
                    for k, v in _methods.items()
                    if not isinstance(v, ModuleType)}

        super(Server, self).__init__(
            methods=_methods, name=name, context=context, pool_size=pool_size,
            heartbeat=heartbeat)

    @staticmethod
    def _filter_methods(cls, self, methods):
        # Override method to not restrict methods to only callables.
        if isinstance(methods, dict):
            return methods
        server_methods = set(k for k in dir(cls) if not k.startswith('_'))

        if isinstance(methods, ModuleType) \
                or methods.__module__ == '__builtin__':
            prefix = methods.__name__
        else:
            prefix = '{}.{}'.format(
                methods.__module__, methods.__class__.__name__)

        return {'{}.{}'.format(prefix, k): getattr(methods, k)
                for k in dir(methods) if not k.startswith('_')
                and k not in server_methods}

    def _inject_builtins(self):
        super(Server, self)._inject_builtins()
        self._methods['_schema'] = lambda: self._schema

    def _async_task(self, initial_event):
        # Override method to completely serialize exceptions. By default
        # zerorpc raises a RemoteError with the server-side exception details.
        # That's fine if your code catches general errors for debugging, but
        # does not work for code-flow where you catch specific errort types.
        # Such as how most of `os.path` methods work where they catch OSError
        # and change how they operate based on that.

        protocol_v1 = initial_event.header.get(u'v', 1) < 2
        channel = self._multiplexer.channel(initial_event)
        hbchan = zerorpc.HeartBeatOnChannel(
            channel, freq=self._heartbeat_freq, passive=protocol_v1)
        bufchan = zerorpc.BufferedChannel(hbchan)
        exc_infos = None
        event = bufchan.recv()
        try:
            self._context.hook_load_task_context(event.header)
            functor = self._methods.get(event.name, None)
            if functor is None:
                raise NameError(event.name)
            functor.pattern.process_call(
                self._context, bufchan, event, functor)
        except zerorpc.LostRemote:
            exc_infos = list(sys.exc_info())
            self._print_traceback(protocol_v1, exc_infos)
        except Exception as e:
            # exc_infos = list(sys.exc_info())
            # human_exc_infos = self._print_traceback(protocol_v1, exc_infos)
            reply_event = bufchan.new_event(
                u'ERR', self.encoder.serializer.serialize(e),
                self._context.hook_get_task_context())
            self._context.hook_server_inspect_exception(
                event, reply_event, exc_infos)
            bufchan.emit_event(reply_event)
        finally:
            del exc_infos
            bufchan.close()


class ErrorHandlingMiddleware(object):
    """
    Middleware object for handling errors. This should be added to our modified
    client to handle server side serialized exceptions.
    """
    def __init__(self, encoder):
        self.encoder = encoder

    def client_handle_remote_error(self, event):
        """
        Handle a remote error on the client.

        Parameters
        ----------
        event : zerorpc.Event

        Returns
        -------
        Exception
        """
        if event.header.get(u'v', 1) >= 2:
            return self.encoder.serializer.deserialize(event.args)
        else:
            (msg,) = event.args
            return zerorpc.RemoteError('RemoteError', msg, None)


class Client(zerorpc.Client):
    """
    Modified zerorpc client that adds extra functionality.
    """

    def __init__(self, *args, **kwargs):
        encoder = kwargs.pop('encoder', None)
        if encoder is None:
            encoder = Encoder()
        self.encoder = encoder

        super(Client, self).__init__(*args, **kwargs)

        self._context.register_middleware(
            ErrorHandlingMiddleware(self.encoder))

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

        payload = self.encoder.encode(*args, **kwargs)

        return self.encoder.serializer.deserialize(
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

        # # IPython fix
        # if item in ('trait_names', '_getAttributeNames'):
        #     return self._methods

        schema = self._schema.get(item)

        if schema == Schema.VALUE:
            return self(item)

        elif schema == Schema.MODULE:
            # Return our ProxyModule shim object.
            return ProxyModule(self, item)

        # Ensure method is valid.
        if item not in self._methods:
            raise AttributeError('{!r} has no attribute {!r}'.format(
                self._name, item))

        return lambda *args, **kargs: self(item, *args, **kargs)
