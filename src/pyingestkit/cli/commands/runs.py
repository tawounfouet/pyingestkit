from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pyingestkit.cli.common import metadata_store_or_exit, project_config_or_exit
from pyingestkit.cli.console import console


def _local_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _status_style(status: str) -> str:
    if status == "SUCCESS":
        return "green"
    if status == "FAILED":
        return "red"
    return "yellow"


def runs_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", "-w", file_okay=False, dir_okay=True),
    ] = None,
    job_id: Annotated[str | None, typer.Option("--job", help="Filter by job ID.")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Filter by run status.")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=1000)] = 50,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """List persisted ingestion runs from the configured MetadataStore."""
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    store = metadata_store_or_exit(project_config, workspace=effective_workspace)
    rows = store.list_runs(job_id=job_id, status=status, limit=limit)
    if json_output:
        payload = [
            {
                "run_id": row.run_id,
                "job_id": row.job_id,
                "job_version": row.job_version,
                "status": row.status,
                "started_at": row.started_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration_seconds": row.duration_seconds,
                "error": row.error,
            }
            for row in rows
        ]
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return

    table = Table(title="Recent ingestion runs", show_header=True, header_style="bold")
    table.add_column("Timestamp")
    table.add_column("Run")
    table.add_column("Job")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    for row in rows:
        style = _status_style(row.status)
        duration = f"{row.duration_seconds:.3f}s" if row.duration_seconds is not None else "—"
        table.add_row(
            _local_time(row.started_at),
            row.run_id[:8],
            row.job_id,
            f"[{style}]{row.status}[/{style}]",
            duration,
        )
    console.print(table)
