from __future__ import absolute_import, print_function

import functools

import mock

from .pipes import Client
from .log import get_logger


_logger = get_logger(__name__)


class PatchedClient(Client):
    """
    A modified zerorpc Client that temporarily patches remote server methods
    when used as a context manager.
    """

    def __init__(self, **kwargs):
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
        super(PatchedClient, self).__init__(**kwargs)
        self._ctxs = []  # List[mock._patch]

    def __iter__(self):
        for func_name in self._methods:

            # Handle cases such as patching `open`.
            if '.' not in func_name:
                patch_name = '__builtin__.{}'.format(func_name)
            else:
                patch_name = func_name

            _logger.debug('Patching {!r}'.format(func_name))

            yield mock.patch(
                patch_name, autospec=True,
                side_effect=functools.partial(self, func_name))

    def __enter__(self):
        for ctx in iter(self):
            try:
                ctx.__enter__()
            except ImportError:
                pass
            self._ctxs.append(ctx)
        return super(PatchedClient, self).__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctxs:
            for ctx in reversed(self._ctxs):
                ctx.__exit__()
        self._ctxs = []
        return super(PatchedClient, self).__exit__(exc_type, exc_val, exc_tb)


def rio(connect_to, context=None, timeout=8.0, heartbeat=5.0,
        passive_heartbeat=True):
    """
    Get a context manager for executing remote methods.

    Parameters
    ----------
    connect_to : str
    context : Optional[Any]
    timeout : float
    heartbeat : float
    passive_heartbeat : bool

    Returns
    -------
    _Patched
    """
    kwargs = {
        'connect_to': connect_to,
        'context': context,
        'timeout': timeout,
        'heartbeat': heartbeat,
        'passive_heartbeat': passive_heartbeat,
    }
    return PatchedClient(**kwargs)
