"""
Helper for gathering all filesystem methods to be hosted by a rio server.
"""
import os
import pathlib


from typing import *


_FS_METHODS_EXCLUDE = frozenset((
    'os.path.join',
    'os.path.dirname',
    'os.path.split',
    'os.path.basename',
))


def iterfsmethods(includes=None, excludes=_FS_METHODS_EXCLUDE):
    """
    Yield all file system methods.

    Parameters
    ----------
    includes : Optional[Container[str]]
    excludes : Optional[Container[str]]

    Returns
    -------
    Iterator[str, Callable]
    """
    # Use pathlib accessor object to get the list of method names to cache.
    names = [s for s in dir(pathlib._NormalAccessor) if s[0] != '_']

    for name in names:
        fullname = 'os.{}'.format(name)
        if excludes and fullname in excludes:
            continue
        if includes and fullname not in includes:
            continue
        obj = getattr(os, name, None)
        if obj is not None:
            yield fullname, obj

    for name in os.path.__all__:
        fullname = 'os.path.{}'.format(name)
        if excludes and fullname in excludes:
            continue
        if includes and fullname not in includes:
            continue
        obj = getattr(os.path, name, None)
        if obj is not None:
            yield fullname, obj

    for name in names:
        fullname = 'pathlib._NormalAccessor.{}'.format(name)
        if excludes and fullname in excludes:
            continue
        if includes and fullname not in includes:
            continue
        yield fullname, getattr(pathlib._NormalAccessor, name)
