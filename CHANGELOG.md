# Changelog

All notable changes to PyIngestKit are documented here.

## [0.1.1] - 2026-09-03

### Changed
- Replaced the `argparse` CLI with Typer.
- Added Rich tables, panels, formatted errors, and help rendering.
- Added `pyingest help` in addition to native `--help` / `-h` support.
- Added `--json` machine-readable output to `jobs`, `inspect`, and `run`.
- Added `-V` as an alias for `--version` and `-w` for `--workspace`.
- Split CLI implementation into app, command, console, and common helper modules.
- Amended ADR-002: the ingestion runtime remains stdlib-only while Typer/Rich are isolated CLI dependencies.

### Dependencies
- Added `typer>=0.26,<0.28`.
- Added `rich>=15.0,<16`.

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
- Standard-library-only runtime.
