# Example plugin package

A real job package can expose PyIngestKit jobs with:

```toml
[project.entry-points."pyingestkit.jobs"]
demo = "my_jobs:job"
```

The exposed object may be a `Job` instance, a `Job` subclass, or a zero-argument factory returning a `Job`.
