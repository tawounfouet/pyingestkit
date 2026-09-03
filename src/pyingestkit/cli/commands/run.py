from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.artifacts.filesystem import LocalArtifactStore
from pyingestkit.cli.common import get_job_or_exit, get_registry, parse_params_json
from pyingestkit.cli.console import console
from pyingestkit.runtime.runner import Runner


def run_command(
    job_id: Annotated[str, typer.Argument(help="Namespaced ingestion job ID to execute.")],
    workspace: Annotated[
        Path,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace used for run artifacts.",
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path(".pyingest"),
    fixture: Annotated[
        bool,
        typer.Option("--fixture", help="Run in fixture mode for reproducible/offline inputs."),
    ] = False,
    params_json: Annotated[
        str,
        typer.Option("--params-json", help="Runtime parameters encoded as a JSON object."),
    ] = "{}",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """Execute an installed ingestion job."""
    job = get_job_or_exit(get_registry(), job_id)
    parameters = parse_params_json(params_json)

    runner = Runner(LocalArtifactStore(workspace))
    result = runner.run(job, parameters=parameters, fixture_mode=fixture)
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
        console.print_json(json.dumps(payload))
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
