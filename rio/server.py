from __future__ import absolute_import, division, print_function

import os

from .pipes import Server, iter_find_methods


# NOTE: Stores both name and module because technically os.path is a dynamic
# passthru to a different module - however we want to access it using the
# `os.path` route/name.
_FILESYSTEM_CALLS = {
    ('os', os): {
        'os.stat',
        'os.path',
        'os.path.exists',
    },
}


def host_os(url='tcp://0.0.0.0:4242'):

    methods = {}

    for (name, mod), includes in _FILESYSTEM_CALLS.items():
        methods[name] = mod
        for k, v in iter_find_methods(mod, prefix=name, recursive=True):
            if k in includes:
                methods[k] = v

    s = Server(methods=methods, name='ros')

    s.bind(url)

    print('starting server @ tcp://0.0.0.0:4242')
    for k, v in sorted(s._methods.items()):
        print('  {} ({})'.format(k, s._schema.get(k)))

    s.run()
