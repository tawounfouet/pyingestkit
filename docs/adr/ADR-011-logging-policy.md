# ADR-011 — Logging policy

**Status:** Accepted  
**Date:** 2026-09-03

## Context

PyIngestKit is both a reusable Python framework and a CLI application. Logging must therefore integrate cleanly with Python applications, third-party libraries, job plugins, CI/CD systems, and observability stacks without forcing a proprietary logging API on plugin authors.

## Decision

PyIngestKit uses the Python standard-library `logging` API throughout framework and plugin-facing code.

```python
import logging

logger = logging.getLogger(__name__)
```

PyIngestKit modules **emit log records but do not configure handlers at import time**.

The application boundary — currently the `pyingest` CLI — configures handlers explicitly.

The CLI supports three console formats:

```text
rich   → interactive human-readable terminal output
plain  → conventional text logs
json   → structured machine-readable logs
```

`RichHandler` is used only as a presentation handler. It does not replace Python's logging API.

Optional rotating file logs use `RotatingFileHandler`. JSON is the default file format because it is suitable for log collectors and automated analysis.

Runtime context is propagated with `contextvars` and can enrich records with:

```text
run_id
job_id
step
```

Handlers apply basic secret redaction for common credential patterns before emission.

## Why not Loguru as the framework contract?

Loguru provides an excellent developer experience for standalone applications and scripts, but PyIngestKit is a reusable framework with independently developed plugins. Standard logging provides the broadest interoperability with Python libraries and lets the consuming application decide how records are routed.

Using standard logging internally also avoids requiring plugin packages to adopt a PyIngestKit-specific logger implementation. A consuming application may still bridge standard logging to Loguru if it chooses to use Loguru globally.

## Consequences

Positive:

- native interoperability with Python libraries and frameworks;
- plugins use conventional `logging.getLogger(__name__)`;
- no handler side effects during import;
- Rich terminal UX remains available;
- JSON and rotating file logging are supported;
- logs can be enriched with ingestion context;
- consuming applications retain control of final logging policy.

Trade-offs:

- standard logging configuration is more verbose than Loguru;
- PyIngestKit owns a small logging configuration layer;
- advanced observability integrations may later require handlers/adapters.

## Future extensions

Potential adapters may be added for OpenTelemetry or other observability backends without changing the framework logging API.

## V0.1.5 stabilization

The terminal convention is frozen as local `YYYY-MM-DD HH:mm:ss`, colored level, short 8-character run ID, job ID and optional step. Full UUIDs and timezone-aware ISO-8601 timestamps remain in structured JSON/metadata. Step lifecycle boundaries are INFO; technical implementation detail is DEBUG. `-v` selects DEBUG and `-q` WARNING. Operational logs remain distinct from persisted runtime events (ADR-015).
