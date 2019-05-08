### Host
```python
python -c "import rio.server; rio.server.start()"
```

### Remote

```python
import os
import rio


sock = 'tcp://127.0.0.1:4242'

# remote call
with rio.RIO(sock):
    assert os.path.exists('/tmp')
```
