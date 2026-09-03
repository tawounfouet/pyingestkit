# Changelog

All notable changes to PyIngestKit are documented here.

## [0.1.4] - 2026-09-03

### Added

- Production-grade logging configuration based on the Python standard `logging` API.
- Rich, plain-text, and structured JSON console log formats.
- Optional rotating file logging with independent level and format.
- Context propagation for `run_id`, `job_id`, and `step` using `contextvars`.
- Basic credential redaction for common password/token/API-key patterns.
- Runtime lifecycle logging in the runner, artifact store, and plugin discovery.
- `--log-level` and `--log-format` CLI overrides.
- ADR-011 documenting the logging policy and the decision not to impose Loguru on framework plugins.
- Logging architecture documentation.

### Changed

- Version bumped to 0.1.4.
- Demo configuration enables a rotating JSON file log in `.pyingest-demo/logs/`.

## [0.1.3] - 2026-09-03

### Added
- Added a real installable demo job package under `examples/plugin_package`.
- Added the `pyingestkit.jobs` entry point `demo-local-file` exposing `demo.local_file`.
- Added `examples/plugin_package/demo.yml` and a bundled sample input file.
- Added repeatable `--param/-p KEY=VALUE` support to `pyingest run`.
- Added typed CLI parameter parsing using YAML scalar semantics.
- Added contract tests for the demo package, entry-point declaration, demo configuration, and zero-argument job contract.

### Changed
- Refactored the local-file demo job so discovery requires no constructor arguments.
- Runtime source paths are now supplied through `RunContext.parameters`.
- Updated the standalone Python example to use the same runtime-parameter model as the plugin package.
- Documented the distinction between a standalone Python example and an installed PyIngestKit job pack.
- Documented installation and end-to-end use of the bundled demo package.
- Invalid YAML project configuration is now converted into a clean CLI error instead of escaping as an uncaught framework exception.

### Fixed
- Fixed the mismatch where documentation described a demo plugin but the delivered `examples/plugin_package` contained only a README.
- Fixed the user-visible situation where `python examples/simple_local_job.py` worked but `pyingest inspect demo.local_file` failed because no entry point was actually installed.
- Added the previously documented `examples/plugin_package/demo.yml` file.

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
