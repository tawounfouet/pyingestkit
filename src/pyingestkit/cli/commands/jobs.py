from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.cli.common import get_registry_with_diagnostics
from pyingestkit.cli.console import console, error_console
from pyingestkit.logging import redact_text


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
            error_console.print(
                f"  [yellow]- {failure.entry_point}:[/yellow] {redact_text(failure.error)}"
            )

    if json_output:
        payload = [
            {
                "id": job.id,
                "version": job.version,
                "description": job.description,
                "requires_artifacts": job.requires_artifacts,
                "requires_metadata": job.requires_metadata,
            }
            for job in jobs
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
    table.add_column("Required Backends")
    table.add_column("Description")
    for job in jobs:
        reqs: list[str] = []
        if job.requires_artifacts:
            reqs.append(f"artifacts: {job.requires_artifacts}")
        if job.requires_metadata:
            reqs.append(f"metadata: {job.requires_metadata}")
        reqs_str = ", ".join(reqs) if reqs else "Any"
        table.add_row(job.id, job.version, reqs_str, job.description or "—")
    console.print(table)
