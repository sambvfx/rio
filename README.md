`rio` is a library for temporarily patching python objects so they are executed by a remote server. It's built using [mock](https://docs.python.org/3/library/unittest.mock.html) and [zerorpc](https://www.zerorpc.io/) and can be used without changing existing code. The methods that are patched are determined by the *server*.

Example
-------

Lets pick a host machine to serve our remote methods. For the sake of this example, this server's cname is `sv-rio01`.
### Host [sv-rio01]

First lets just touch a path on disk.

```bash
$ touch /tmp/example
```

Then start up a server on port `4242`. For now we'll only bother hosting/patching `os.path.exists`.

```python
import os
import rio.server

methods = {
    'os.path.exists': os.path.exists,
}

rio.server.start(methods=methods, port=4242)
```

> TIP: Check out `rio.packages.fs` to see helpers to patch *all* filesystem methods.

Next we can test it's working by running some python from a different machine.

### Client

```python
import os
from rio import rio


# connection string to connect Client->Server
remotefs = 'tcp://sv-rio01:4242'

path = '/tmp/example'

# local call
assert not os.path.exists(path)

# remote call
with rio(remotefs):
    assert os.path.exists(path)
```
