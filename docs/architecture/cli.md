# CLI architecture

PyIngestKit V0.1.1 uses **Typer** for command contracts and **Rich** for terminal rendering.

```text
pyingest
├── jobs
├── inspect <job-id>
├── run <job-id>
└── help
```

Native help is available through:

```bash
pyingest --help
pyingest jobs --help
pyingest inspect --help
pyingest run --help
```

`pyingest help` is retained as a discoverability alias for the root help screen.

Human-facing output uses Rich tables and panels. Commands that expose structured data also provide `--json` for scripting and automation.

The CLI is deliberately isolated from the ingestion runtime:

```text
Typer / Rich
    │
    ▼
pyingestkit.cli
    │
    ▼
PyIngestKit runtime (stdlib-only)
```
