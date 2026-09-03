# Logging

PyIngestKit uses standard Python `logging`; the CLI owns handler configuration. Rich is the human terminal renderer. JSON is used for structured file/CI output.

Official terminal shape:

```text
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file] Run started
2026-09-03 17:42:03  INFO    [run=785c1cdc job=demo.local_file step=FetchLocal] Step started
```

Terminal timestamps are local and run IDs short. JSON/DB timestamps are timezone-aware ISO-8601 and UUIDs remain full. Lifecycle boundaries are INFO; technical details are DEBUG. `-v` maps to DEBUG and `-q` to WARNING. Logs go to stderr so JSON command payloads remain clean on stdout.
