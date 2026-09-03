# Declarative API

The recommended API uses `@step` and `@job`. During `JobDefinition.build()`, a context-local `PipelineBuilder` records sequential `StepInvocation` objects without running step functions. Invocations compile to imperative `Step` instances.

Guardrails: deterministic sequential builds, no nested builds, no generic DAG scheduler, no implicit parallelism, no hidden direct execution. Use `step_definition.fn(...)` for unit tests.
