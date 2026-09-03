from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.cli.common import get_registry
from pyingestkit.cli.console import console


def jobs_command(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """List installed ingestion jobs."""
    jobs = get_registry().list()

    if json_output:
        console.print_json(
            json.dumps(
                [
                    {
                        "id": job.id,
                        "version": job.version,
                        "description": job.description,
                    }
                    for job in jobs
                ]
            )
        )
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
