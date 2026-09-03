# ADR-003 — Plugin discovery via Python entry points

**Status:** Accepted for V0.1

## Decision

Installed job packs are discovered explicitly through `importlib.metadata` entry points. Importing `pyingestkit` never auto-loads plugins.
