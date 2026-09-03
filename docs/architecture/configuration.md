# Configuration

PyIngestKit V0.1.2 uses **Pydantic** for schema validation and **PyYAML** for YAML project configuration.

Example `pyingest.yml`:

```yaml
runtime:
  workspace: .pyingest
  fixture_mode: false
  parameters:
    source: local
```

Run with:

```bash
pyingest run my.namespace.job --config pyingest.yml
```

CLI values override configuration values:

```text
framework defaults
      ↓
pyingest.yml
      ↓
CLI options
```

Unknown configuration keys are rejected instead of being silently ignored.
