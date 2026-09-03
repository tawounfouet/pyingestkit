# ADR-017 — Decorator API compiles to imperative model

**Status:** Accepted — V0.1.5

There is one runtime model. `JobDefinition` + `PipelineBuilder` compile step invocations into the existing imperative `Job` / `Pipeline` / `Step` representation. `Runner` executes only that representation.

This prevents two runtimes from diverging and preserves scope discipline inherited from PyWorkflow Engine lessons.
