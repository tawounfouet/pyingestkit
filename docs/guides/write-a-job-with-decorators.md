# Write a job with decorators

```python
from pyingestkit import RunContext, job, step

@step
def fetch(context: RunContext):
    ...

@step
def normalize(data):
    ...

@job(id="example.dataset", version="1.0.0")
def dataset() -> None:
    fetch()
    normalize()
```

Expose the resulting `JobDefinition` through a `pyingestkit.jobs` entry point. Use `normalize.fn(...)` in isolated unit tests.
