# ADR-003 — Plugin discovery via Python entry points

**Status:** Accepted; updated in V0.1.5

Installed job packs are discovered explicitly through `importlib.metadata` entry points. Importing `pyingestkit` never auto-loads plugins.

V0.1.5 accepts `JobDefinition`, `Job` instances, `Job` subclasses, and zero-argument factories. Discovery isolates broken entry points so healthy jobs remain usable; diagnostics are surfaced without turning one plugin failure into a global CLI outage.
