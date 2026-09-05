# Logging

PyIngestKit uses standard Python `logging`; framework modules emit records but do not configure
handlers at import time. The CLI/application boundary owns handler configuration.

Official terminal shape:

```text
2026-09-03 17:42:03  INFO     [run=785c1cdc job=demo.local_file] Run started
2026-09-03 17:42:03  INFO     [run=785c1cdc job=demo.local_file step=FetchLocal] Step started
```

Terminal timestamps are local and run IDs are shortened to eight characters. Structured JSON uses
UTC timezone-aware ISO-8601 timestamps and full IDs. `step` is omitted when not applicable.

Lifecycle boundaries are INFO; implementation detail is DEBUG. `-v` maps to DEBUG and `-q` to
WARNING. Logs go to stderr so successful `--json` command payloads remain clean on stdout.

File logging supports `plain` and `json`, with JSON as the default. Rich is terminal presentation and
is not a file format.

Secret redaction covers common credential key/value pairs, bearer tokens, URL-embedded passwords and
exception text. The stable marker is `***REDACTED***`.

Operational logs remain distinct from persisted runtime events (ADR-015).

See [V1 operational stability contract](../reference/stability-v1.md).
