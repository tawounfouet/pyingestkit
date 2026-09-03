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
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Or use the Makefile bootstrap-aware target:

```bash
make install-dev
```

`make install-dev`, `make security`, `make verify`, and `make release-check` keep the packaging toolchain safe by upgrading `pip` before dependency auditing. This prevents `pip-audit` from failing because of a vulnerable `pip` bundled with a newly created virtual environment rather than because of a PyIngestKit dependency.

## Local checks

```bash
make test
make check
make quality
make security
```

The minimal checks do not require network access once the project dependencies are installed. The security gate may access the package index when its bootstrap step upgrades `pip` and when `pip-audit` resolves vulnerability data.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/check_public_api.py
python -m compileall -q src tests
```
