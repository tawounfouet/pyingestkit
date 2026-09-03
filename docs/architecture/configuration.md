# Configuration

PyIngestKit V0.1.3 uses **Pydantic** for schema validation and **PyYAML** for YAML project configuration.

## Project file

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: false
  parameters:
    source: local
```

Unknown keys are rejected (`extra="forbid"`) so configuration drift fails early.

## Runtime precedence

```text
framework defaults
        ↓
YAML project configuration
        ↓
--params-json
        ↓
--param / -p KEY=VALUE
        ↓
explicit CLI runtime options
```

`--param/-p` is repeatable and uses YAML scalar parsing, preserving values such as booleans and integers.

```bash
pyingest run demo.local_file \
  --param path=examples/plugin_package/data/sample.txt \
  --param retries=3 \
  --param enabled=true
```

## Logging configuration

The root project configuration also accepts a `logging` section:

```yaml
logging:
  level: INFO
  format: rich
  console: true
  file:
    enabled: false
    path: .pyingest/logs/pyingest.log
    level: DEBUG
    format: json
    max_bytes: 10000000
    backup_count: 5
```

`level` and `file.level` are validated by Pydantic. Accepted formats are `rich`, `plain`, and `json`.

The CLI can override the console policy with `--log-level` and `--log-format`.
