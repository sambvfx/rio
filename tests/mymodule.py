import os

import os.path as path


CONST = 42


def a():
    return 1


def b(*args, **kwargs):
    return args, kwargs


class CustomError(Exception):
    pass


def raise_error(exctype=ValueError):
    raise exctype('test error')


class CustomPath(unicode):

    def __div__(self, other):
        return self.__class__(os.path.join(str(self), str(other)))

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, str(self))

    exists = lambda self: os.path.exists(str(self))

    @property
    def parent(self):
        return self.__class__(os.path.dirname(str(self)))

    def stat(self):
        return os.stat(str(self))

    def listdir(self):
        if not self.exists():
            return []
        results = []
        for name in os.listdir(str(self)):
            results.append(self / name)
        return results
