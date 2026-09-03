# ADR-010 — Production-grade dependency policy

**Status:** Accepted  
**Date:** 2026-09-03  
**Supersedes:** ADR-002

## Context

PyIngestKit is intended to be an industrial, reusable Python ingestion framework. A strict zero-third-party-dependency rule would force the project to recreate mature capabilities already provided by established Python packages, increasing custom code, maintenance cost, security burden, and implementation risk.

## Decision

PyIngestKit does **not** pursue a zero-third-party-dependency objective.

Third-party dependencies are allowed in the framework when they:

1. solve a recurring framework-level concern;
2. have a clear responsibility;
3. materially improve correctness, maintainability, developer experience, or security;
4. are actively maintained and broadly adopted;
5. remain replaceable behind PyIngestKit-owned contracts where appropriate.

V0.1.2 establishes the following production baseline:

```text
Typer
→ typed CLI contracts and command routing

Rich
→ human-facing terminal rendering

Pydantic
→ validated configuration models and explicit schemas

PyYAML
→ safe YAML project configuration loading
```

Development and release tooling may use additional packages such as pytest, pytest-cov, pytest-randomly, Ruff, Mypy, Bandit, pip-audit, pre-commit, build, and Twine.

## Dependency governance

Dependencies should follow these rules:

- declare direct runtime dependencies explicitly in `pyproject.toml`;
- use bounded compatible version ranges rather than unbounded dependencies;
- avoid adding a package for trivial helpers that are clearer in the stdlib;
- prefer safe APIs such as `yaml.safe_load`;
- validate configuration at framework boundaries;
- audit dependencies in CI;
- keep business/client-specific libraries out of the generic framework unless a generic adapter explicitly requires them;
- keep large technology-specific integrations optional when their use is not universal.

## Consequences

Positive:

- less bespoke infrastructure code;
- stronger schemas and validation;
- better CLI developer experience;
- easier industrialization;
- clearer configuration contracts.

Trade-offs:

- larger dependency graph;
- dependency upgrade and CVE management become explicit maintenance responsibilities;
- compatibility must be tested in CI.

These trade-offs are accepted as normal responsibilities of a production-grade Python framework.
