# Logging architecture

PyIngestKit separates **log emission** from **log configuration**.

```text
Framework / Job Plugin
        │
        │ logging.getLogger(__name__)
        ▼
Python LogRecord
        │
        ▼
Application / CLI configuration
        │
        ├── RichHandler → stderr
        ├── StreamHandler → stderr
        ├── JSON formatter → stderr
        └── RotatingFileHandler → file
```

## Context

During a run, PyIngestKit enriches records using `contextvars`:

```text
run_id
job_id
step
```

This keeps the context safe across nested calls without passing logger objects through every function.

## Output streams

Human and diagnostic logs are emitted to **stderr**.

Machine command payloads such as `pyingest run --json` remain on **stdout**, so shell pipelines can consume them without log contamination.

## Configuration

Example:

```yaml
logging:
  level: INFO
  format: rich
  console: true
  file:
    enabled: true
    path: .pyingest/logs/pyingest.log
    level: DEBUG
    format: json
    max_bytes: 10000000
    backup_count: 5
```

CLI overrides:

```bash
pyingest run demo.local_file \
  --config pyingest.yml \
  --log-level DEBUG \
  --log-format plain
```

## Library rule

No module is allowed to call `logging.basicConfig()` or attach application handlers at import time.
