# CLI architecture

PyIngestKit uses **Typer** for command contracts and **Rich** for human-facing terminal rendering.

## Commands

```text
pyingest --version
pyingest --help
pyingest help
pyingest jobs
pyingest inspect <job-id>
pyingest run <job-id>
```

`run` supports project configuration:

```bash
pyingest run <job-id> --config pyingest.yml
```

## Human vs machine output

Human-facing output uses Rich tables, panels, and formatted errors.

Machine-facing output deliberately bypasses Rich:

```bash
pyingest jobs --json
pyingest inspect <job-id> --json
pyingest run <job-id> --json
```

JSON and `--version` are emitted as plain text without Rich markup or ANSI escape sequences. This keeps shell scripting, CI parsing, and contract tests deterministic.
