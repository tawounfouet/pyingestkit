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
