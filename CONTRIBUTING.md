# Contributing

## Principles

1. Keep PyIngestKit focused on the ingestion lifecycle.
2. Prefer composition over inheritance.
3. Avoid global mutable runtime state.
4. Avoid import-time side effects.
5. Keep domain/business logic out of PyIngestKit.
6. Add a framework dependency only when it has a clear reusable responsibility.
7. Prefer established production-grade packages over bespoke infrastructure when the trade-off is justified.
8. Keep machine-readable CLI output deterministic and free of presentation formatting.

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Local checks

```bash
make test
make check
make quality
make security
```

The minimal checks do not require network access once the project dependencies are installed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/check_public_api.py
python -m compileall -q src tests
```
