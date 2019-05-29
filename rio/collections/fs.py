"""
Helper for gathering all filesystem methods to be hosted by a rio server.
"""
import os
import pathlib

from typing import Iterator, Tuple, Callable


def iterfsmethods():
    """
    Yield all file system methods.

    Returns
    -------
    Iterator[Tuple[str, Callable]]
    """
    # Use pathlib accessor object to get the list of file system methods.
    names = [s for s in dir(pathlib._NormalAccessor) if s[0] != '_']

    for name in names:
        fullname = 'os.{}'.format(name)
        obj = getattr(os, name, None)
        if obj is not None:
            yield fullname, obj

    for name in names:
        fullname = 'pathlib._NormalAccessor.{}'.format(name)
        yield fullname, getattr(pathlib._NormalAccessor, name)

    yield 'open', open
