from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.cli.common import get_registry_with_diagnostics
from pyingestkit.cli.console import console, error_console


def jobs_command(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """List installed ingestion jobs."""
    registry, failures = get_registry_with_diagnostics()
    jobs = registry.list()

    if failures:
        error_console.print(
            f"[yellow]Warning:[/yellow] {len(failures)} plugin(s) failed to load; "
            "healthy plugins remain available."
        )
        for failure in failures:
            error_console.print(f"  [yellow]- {failure.entry_point}:[/yellow] {failure.error}")

    if json_output:
        payload = [
            {"id": job.id, "version": job.version, "description": job.description} for job in jobs
        ]
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return

    if not jobs:
        console.print(
            Panel.fit(
                "No ingestion jobs discovered. Install a package exposing "
                "[bold]pyingestkit.jobs[/bold] entry points.",
                title="PyIngestKit",
            )
        )
        return

    table = Table(title="Installed ingestion jobs", show_header=True, header_style="bold")
    table.add_column("Job ID", style="bold")
    table.add_column("Version")
    table.add_column("Description")
    for job in jobs:
        table.add_row(job.id, job.version, job.description or "—")
    console.print(table)
