# Contributing

## Principles

1. Keep the core small.
2. Prefer composition over inheritance.
3. Avoid global mutable runtime state.
4. Avoid import-time side effects.
5. Keep domain/business logic out of PyIngestKit.
6. Add a feature to core only when it is directly reusable across ingestion jobs.

## Local checks

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/check_zero_runtime_dependencies.py
python scripts/check_public_api.py
```
