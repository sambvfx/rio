import os

import os.path as path


CONST = 42


def a():
    return 1


def b(*args, **kwargs):
    return args, kwargs


class CustomPath(object):

    existsmeth = staticmethod(os.path.exists)
    statsmeth = staticmethod(os.stat)

    def __init__(self, p):
        self._path = p

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, str(self._path))

    def __str__(self):
        return str(self._path)

    def exists(self):
        return self.existsmeth(str(self))

    def stat(self):
        return self.statsmeth(str(self))
