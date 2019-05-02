from .pipes import Client

from typing import Optional


class hybrid(object):
    """
    Operates as a hybird object where it first attempts to getattr call to a
    see if the remote server has the specified method before falling back on
    the local object.
    """

    def __init__(self, obj, name=None, url='tcp://127.0.0.1:4242'):
        """
        Parameters
        ----------
        obj : object
        name : Optional[str]
        url : str
        """
        self._obj = obj
        if name is None:
            name = getattr(obj, '__name__', None)
            if name is None:
                name = str(obj)
        self._name = name
        self._client = Client(url, prefix=name)

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self._name)

    def __getattr__(self, item):
        try:
            return getattr(self._client, item)
        except AttributeError:
            return object.__getattribute__(self._obj, item)
