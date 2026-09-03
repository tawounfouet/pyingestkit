# ADR-012 — Unified workspace layout

**Status:** Accepted — V0.1.5

PyIngestKit uses one default workspace: `.pyingest/`.

```text
.pyingest/{state,logs,runs,published}
```

Plugins must not silently choose a separate global workspace. Job isolation comes from namespaced IDs and run UUIDs. Alternate workspaces are explicit runtime configuration.
