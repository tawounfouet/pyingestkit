# Changelog

All notable changes to PyIngestKit are documented here.

## [0.1.2] - 2026-09-03

### Changed
- Removed the zero-third-party-dependency architectural constraint.
- Added ADR-010 defining a production-grade dependency policy.
- Marked ADR-002 as superseded.
- Added Pydantic and PyYAML as framework runtime dependencies.
- Added validated YAML project configuration with strict unknown-key rejection.
- Added `--config/-c` to `pyingest run`.
- CLI runtime options override project YAML configuration.
- Machine-readable CLI output now bypasses Rich completely.
- `--version` now emits plain text without ANSI escape codes.

### Fixed
- Fixed `test_version`, which previously failed because Rich colorized the semantic version.
- Fixed `jobs --json` contract testing by emitting raw JSON through Click/Typer instead of `Rich.Console.print_json()`.

### Dependencies
- `typer>=0.27,<0.28`
- `rich>=15,<16`
- `pydantic>=2.11,<3`
- `PyYAML>=6,<7`

## [0.1.1] - 2026-09-03

### Changed
- Replaced the `argparse` CLI with Typer.
- Added Rich tables, panels, formatted errors, and help rendering.
- Added `pyingest help` in addition to native `--help` / `-h` support.
- Added `--json` machine-readable output to `jobs`, `inspect`, and `run`.
- Added `-V` as an alias for `--version` and `-w` for `--workspace`.
- Split CLI implementation into app, command, console, and common helper modules.

## [0.1.0] - 2026-09-03

### Added
- Minimal ingestion core: Job, Step, Pipeline, RunContext.
- Runtime Runner with lifecycle events and standardized results.
- LocalSource and LocalArtifactStore.
- Immutable RAW artifacts with SHA-256 hashing.
- Run manifest generation.
- Basic validation rules and validation reports.
- Atomic local publication.
- Job registry and Python entry-point plugin discovery.
- Minimal CLI: version, jobs, inspect, run.
