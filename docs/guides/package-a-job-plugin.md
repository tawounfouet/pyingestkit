# Package a job plugin

Declare entry points in the job-pack `pyproject.toml`:

```toml
[project.entry-points."pyingestkit.jobs"]
my-job = "my_jobs.module:job_definition"
```

The framework package remains free of business jobs.
