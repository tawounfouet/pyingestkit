# ADR-002 — Zero third-party dependency **core**

**Status:** Amended in V0.1.1  
**Previous status:** Accepted for V0.1.0

## Context

V0.1.0 shipped a standard-library-only distribution because the CLI was implemented with `argparse`.
The CLI is part of the PyIngestKit MVP and is now intentionally implemented with Typer and Rich to provide a production-grade command experience.

## Decision

The **PyIngestKit non-CLI runtime remains free of third-party dependencies**.

Third-party dependencies are allowed in `pyingestkit.cli` when they serve the product CLI directly. V0.1.1 therefore declares:

```text
typer
rich
```

as distribution dependencies.

The following namespaces remain stdlib-only:

```text
core
runtime
sources
artifacts
provenance
validation
publication
plugins
```

A repository check enforces this boundary.

## Consequences

- `pip install pyingestkit` provides a working `pyingest` CLI immediately.
- The ingestion engine remains independent from Typer and Rich.
- Importing or embedding the framework runtime does not require CLI abstractions.
- Future CLI dependencies must remain isolated under `pyingestkit.cli`.
