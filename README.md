### Host
```python
import rio
rio.host_os()
```

### Remote

```python
import rio
os = rio.ros()

# remote call
assert os.path.exists('/tmp')

# local call
user = os.environ['USER']

# remote call
size = os.stat('/tmp').st_size
```
 
 
## TODO:

#### Context manager for temp patching of os.

Something like...
```python
import os
import rio


LA = 'tcp://127.0.0.1:4242'


with rio.ros(LA):
    assert os.path.exists('/tmp')
```
