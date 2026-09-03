# ADR-016 — Declarative decorator API

**Status:** Accepted — V0.1.5

`@job` and `@step` are the recommended job-authoring API. The imperative classes remain public for advanced/dynamic use.

Decorated steps expose `.fn(...)` for direct unit testing. A normal call outside a job build is rejected to avoid ambiguous magic.

Generic DAG scheduling, distributed dependencies, generic timeout semantics and worker orchestration are explicitly out of scope.
