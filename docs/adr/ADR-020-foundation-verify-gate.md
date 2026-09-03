# ADR-020 — Foundation freeze requires `make verify`

**Status:** Accepted — V0.1.6

## Decision

The V0.1.x Foundation is considered releasable for V0.2 work only when the aggregate verification target succeeds in the reference development/CI environment:

```bash
make verify
```

The target aggregates functional/contract tests, public API and compile checks, Ruff linting and formatting, Mypy strict typing, Bandit, pip-audit, and package builds.

## Rationale

V0.1.5 demonstrated that green functional tests alone do not prove a production-grade foundation: static quality and security gates can still be red. The aggregate gate prevents that ambiguity from recurring.
