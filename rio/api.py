from __future__ import absolute_import, print_function

import functools

import mock

from .pipes import Client
from .log import get_logger


_logger = get_logger(__name__)


class rio(object):
    """
    Context manager for temporarily patching methods hosted by a remote server.
    """

    def __init__(self, target, **kwargs):
        """
        Parameters
        ----------
        target : str
            e.g. 'tcp://127.0.0.1:4242'
        timeout : float
            Used for the zerorpc.Client as the timeout value.
        heartbeat : float
        passive_heartbeat : bool
        """
        kwargs['connect_to'] = target
        # Defaults
        kwargs.setdefault('timeout', 8.0)
        kwargs.setdefault('heartbeat', 5.0)
        kwargs.setdefault('passive_heartbeat', True)
        self._client_kwargs = kwargs

        self._ctxs = []  # List[Tuple[str, mock._patch]]
        self._client = None  # type: Client

    def __call__(self, func_name, *args, **kwargs):
        return self._client(func_name, *args, **kwargs)

    def __iter__(self):
        self._client = Client(**self._client_kwargs)

        for func_name in self._client._methods:

            _logger.debug('Patching {!r}'.format(func_name))

            yield func_name, mock.patch(
                func_name, autospec=True,
                side_effect=functools.partial(self, func_name))

    def __enter__(self):
        for name, ctx in iter(self):
            try:
                ctx.__enter__()
            except ImportError:
                pass
            self._ctxs.append((name, ctx))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctxs:
            for _, ctx in reversed(self._ctxs):
                ctx.__exit__()
        self._ctxs = []
        self._client.close()
        self._client = None
