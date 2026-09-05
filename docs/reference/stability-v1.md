# PyIngestKit V1 — Operational Stability Contract

Status: **V1.0.0-b1 — Plugin / Config / Error / CLI / Observability Stability**

This document finalizes the operational public surfaces deliberately deferred by A1/A2:

- external job-plugin discovery;
- project/environment configuration;
- canonical framework errors and deprecation UX;
- CLI command/option/exit-code semantics;
- logging and observability helpers.

The machine-readable source of truth is `tests/contract/fixtures/stability_v1.json`, enforced by
`scripts/check_v1_stability.py` and therefore by `make check` / `make release-check`.

## 1. Baseline

B1 starts from the qualified A2 merge commit:

```text
eccb7f65a05707c2f7ea9a9881c930a641d65b92
```

A1/A2 public namespace and compatibility gates remain active. B1 adds a third layer; it does not
replace or weaken either earlier contract.

## 2. Plugin contract

External job packs use the stable entry-point group:

```toml
[project.entry-points."pyingestkit.jobs"]
my-job = "my_package.jobs:job_definition"
```

Accepted values are:

- a `JobDefinition`;
- a `Job` instance;
- a `Job` subclass with a zero-argument constructor;
- a zero-argument factory returning `Job` or `JobDefinition`.

Discovery order is deterministic by `(entry_point.name, entry_point.value)`. This prevents package
installation order from changing duplicate-resolution behavior.

Duplicate logical `job.id` values are not allowed. The first deterministic entry point is retained;
later duplicates are isolated as `PluginFailure` records. A broken plugin never hides healthy jobs.

Library behavior and CLI behavior are intentionally different:

```text
discover_jobs()                strict=True by default
load_registry()                tolerant; healthy jobs remain usable
load_registry_with_diagnostics tolerant + PluginFailure details
```

This distinction is stable in 1.x.

## 3. Configuration contract

### 3.1 Configuration-file resolution

The stable resolution order is:

```text
explicit --config
  -> PYINGEST_CONFIG
  -> PYINGEST_ENV -> pyingest.yml.<env>
  -> pyingest.yml / pyingestkit.yml / .pyingest.yml
  -> in-memory defaults
```

The machine source tokens exposed by `pyingest config --json` are:

```text
explicit
environment
profile
default_file
in_memory
```

`PYINGEST_CONFIG` and `PYINGEST_ENV` are fail-closed selectors. If either explicitly selects a
configuration that does not exist, PyIngestKit returns a controlled configuration error instead of
silently falling through to another profile.

`PYINGEST_ENV` is a simple profile identifier composed of letters, digits, `.`, `_` and `-`; path
traversal or path separators are rejected.

### 3.2 Workspace precedence

Workspace selection is:

```text
explicit --workspace
  -> PYINGEST_WORKSPACE
  -> runtime.workspace from YAML
  -> .pyingest default
```

`PYINGEST_WORKSPACE` is therefore a real runtime override, not merely a documented example variable.

### 3.3 Dotenv bootstrap

The console entry point loads dotenv files only from the current working directory. It never searches
parents.

When a profile is selected, candidates are:

```text
envs/.env.<env>
.env.<env>
```

followed by root `.env`. Precedence is:

```text
OS environment > profile dotenv > root .env
```

A root `.env` may itself select `PYINGEST_ENV`; the selected profile file is still loaded before root
values are applied.

Files ending in `.example` are templates only. They are **never** auto-loaded at runtime.

### 3.4 YAML model behavior

Pydantic configuration models remain frozen and `extra="forbid"`. Unknown keys fail early rather
than being silently ignored.

Configuration secrets remain references to environment variables. Inline provider credentials are
not added to the project model.

## 4. Canonical error namespace

The canonical V1 import path is:

```python
import pyingestkit.errors as errors
```

It exposes framework, HTTP and target error families through one namespace. These exports are aliases
to the existing historical classes, not replacements. Exception identity is preserved:

```python
pyingestkit.errors.PluginError is pyingestkit.core.exceptions.PluginError
```

The same rule applies to HTTP and target error classes. Existing `except` clauses therefore continue
to work.

`IngestionError` remains the base class for controlled ingestion failures; more specialized provider
errors inherit from the appropriate framework family.

## 5. Deprecation policy

Public V1 deprecations use:

```python
from pyingestkit.deprecations import PyIngestKitDeprecationWarning, warn_deprecated
```

`PyIngestKitDeprecationWarning` inherits `FutureWarning` intentionally, making user-facing migration
warnings visible under Python's normal warning filters.

For stable V1 public APIs, the compatibility policy is:

```text
introduce replacement
  -> retain old path/alias
  -> emit PyIngestKitDeprecationWarning
  -> document migration
  -> keep compatibility throughout 1.x
  -> remove only in a later breaking major release
```

A security/correctness emergency may require an exceptional change, but it must be explicitly
recorded and release-noted.

## 6. CLI contract

The stable console entry point is `pyingest`.

Stable command names are:

```text
config
help
inspect
jobs
published
replay
run
runs
status
versions
```

The exact option aliases and positional argument names are snapshotted in `stability_v1.json`.
Typer's generated `--install-completion` and `--show-completion` options are intentionally disabled;
they are not PyIngestKit V1 product contracts.

### Exit-code classes

```text
0  success/help/version/valid empty result
2  usage, argument, configuration, lookup-selection error
1  runtime/domain execution failure
```

Representative examples:

- unknown CLI command -> `2`;
- invalid config or unknown job -> `2`;
- a run/replay execution failure -> `1`;
- no currently published version -> `1` with a controlled message;
- an empty `versions`/`runs` listing -> `0`.

### Output stability

`--json` stabilizes successful machine-readable payload semantics. Errors remain on stderr with the
canonical `Error:` prefix and the appropriate exit code.

Human output stability is semantic rather than pixel-level. Command headings, important labels,
identifiers and warning/error prefixes are part of the contract; Rich colors, terminal wrapping and
spacing are presentation details.

`config --show-secrets` remains explicit opt-in behavior. Normal configuration inspection masks
credential-bearing DSNs.

## 7. Observability contract

PyIngestKit uses Python standard-library `logging`; importing the framework does not configure root
handlers. Handler configuration occurs explicitly at the application/CLI boundary.

Public helpers are:

```text
configure_logging
current_log_context
log_context
redact_mapping
redact_text
```

### Human terminal format

The canonical human-readable shape is:

```text
YYYY-MM-DD HH:mm:ss  LEVEL    [run=<8-char-id> job=<job_id> step=<step_name>] Message
```

`step` is omitted when not applicable. Terminal timestamps use local timezone. Human run IDs are
shortened to eight characters.

### Structured JSON format

Structured logs use timezone-aware UTC ISO-8601 timestamps and retain full identifiers. Base fields
are:

```text
timestamp
level
logger
message
```

Context fields are added when available:

```text
run_id
job_id
step
```

`exception` is added for exception records.

### File logging

Stable file formats are only:

```text
plain
json
```

`rich` is terminal presentation and is rejected for file logging rather than silently treated as
plain text. JSON remains the default file format.

### Redaction

Logging and CLI failure boundaries redact common secret keys, bearer tokens and URL-embedded
passwords using the marker:

```text
***REDACTED***
```

Exception text is redacted as well as normal log messages.

Persisted runtime events remain distinct from operational logs; B1 does not merge those concepts.

## 8. Stability gate

`make check` now runs three V1 governance layers:

```text
scripts/check_public_api.py          # A1 namespace inventory
scripts/check_v1_compatibility.py    # A2 structural/persistence compatibility
scripts/check_v1_stability.py        # B1 operational surfaces
```

`make release-check` inherits all three gates.

## 9. What remains for B2 and RC1

B1 does not claim V1 is ready for final release. Remaining milestones are:

- **V1.0.0-b2** — qualify representative real-world pilots and complete user-facing documentation;
- **V1.0.0-rc1** — full release/upgrade/security qualification and release candidate packaging;
- **V1.0.0 stable** — final version bump, immutable tag and stable release publication after all
  post-merge checks pass.
