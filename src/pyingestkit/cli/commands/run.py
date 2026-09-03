from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.artifacts.filesystem import LocalArtifactStore
from pyingestkit.cli.common import (
    fail,
    get_job_or_exit,
    get_registry,
    parse_param_assignments,
    parse_params_json,
)
from pyingestkit.cli.console import console
from pyingestkit.config import LogOutputFormat, PyIngestKitConfig, load_config
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.logging import configure_logging
from pyingestkit.runtime.runner import Runner


def run_command(
    job_id: Annotated[str, typer.Argument(help="Namespaced ingestion job ID to execute.")],
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="YAML project configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    workspace: Annotated[
        Path | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace used for run artifacts. Overrides configuration.",
            file_okay=False,
            dir_okay=True,
        ),
    ] = None,
    fixture: Annotated[
        bool | None,
        typer.Option(
            "--fixture/--no-fixture",
            help="Enable or disable fixture mode. Overrides configuration.",
        ),
    ] = None,
    params_json: Annotated[
        str | None,
        typer.Option(
            "--params-json",
            help="Runtime parameters encoded as a JSON object; overrides matching YAML values.",
        ),
    ] = None,
    param: Annotated[
        list[str] | None,
        typer.Option(
            "--param",
            "-p",
            help="Runtime parameter as KEY=VALUE. Repeatable; overrides YAML/--params-json values.",
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="Override the configured logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
        ),
    ] = None,
    log_format: Annotated[
        LogOutputFormat | None,
        typer.Option(
            "--log-format",
            help="Override console log format: rich, plain, or json.",
            case_sensitive=False,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """Execute an installed ingestion job."""
    try:
        project_config = load_config(config) if config is not None else PyIngestKitConfig()
    except ConfigurationError as exc:
        fail(str(exc), code=2)

    try:
        configure_logging(
            project_config.logging,
            level_override=log_level,
            format_override=log_format,
        )
    except ValueError as exc:
        fail(str(exc), code=2)

    job = get_job_or_exit(get_registry(), job_id)
    effective_workspace = workspace or project_config.runtime.workspace
    effective_fixture = fixture if fixture is not None else project_config.runtime.fixture_mode
    parameters = dict(project_config.runtime.parameters)
    if params_json is not None:
        parameters.update(parse_params_json(params_json))
    parameters.update(parse_param_assignments(param))

    runner = Runner(LocalArtifactStore(effective_workspace))
    result = runner.run(job, parameters=parameters, fixture_mode=effective_fixture)
    payload = {
        "run_id": result.run_id,
        "job_id": result.job_id,
        "job_version": result.job_version,
        "status": result.status.value,
        "duration_seconds": round(result.duration_seconds, 6),
        "error": result.error,
        "warnings": list(result.warnings),
    }

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        status_style = "bold green" if result.succeeded else "bold red"
        console.print(
            Panel.fit(
                f"[{status_style}]{result.status.value}[/{status_style}]  "
                f"[bold]{result.job_id}[/bold]\n"
                f"run_id: {result.run_id}\n"
                f"duration: {result.duration_seconds:.3f}s",
                title="PyIngestKit Run",
            )
        )

        steps = Table(title="Steps", show_header=True, header_style="bold")
        steps.add_column("Step")
        steps.add_column("Status")
        steps.add_column("Duration", justify="right")
        for step in result.steps:
            steps.add_row(step.step_name, step.status.value, f"{step.duration_seconds:.3f}s")
        console.print(steps)

        if result.error:
            console.print(f"[bold red]Error:[/bold red] {result.error}")
        for warning in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    if not result.succeeded:
        raise typer.Exit(code=1)
