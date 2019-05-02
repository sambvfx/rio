import os

from .server import host_os
from .proxy import hybrid


def ros():
    print('fetching client @ tcp://127.0.0.1:4242')
    return hybrid(os, name='os', url='tcp://127.0.0.1:4242')
