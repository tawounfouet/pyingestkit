from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pyingestkit.cli.common import fail, metadata_store_or_exit, project_config_or_exit
from pyingestkit.cli.console import console


def status_command(
    run_id: Annotated[str, typer.Argument(help="Full run UUID or unique prefix.")],
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Inspect one persisted run, its steps, artifacts, and runtime events."""
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    store = metadata_store_or_exit(project_config, workspace=effective_workspace)
    try:
        run = store.get_run(run_id)
    except KeyError:
        fail(f"Unknown run: {run_id}", code=2)
    except ValueError as exc:
        fail(str(exc), code=2)
    steps = store.list_steps(run.run_id)
    artifacts = store.list_artifacts(run.run_id)
    events = store.list_events(run.run_id)

    if json_output:
        payload = {
            "run": {
                "run_id": run.run_id,
                "job_id": run.job_id,
                "job_version": run.job_version,
                "status": run.status,
                "started_at": run.started_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration_seconds": run.duration_seconds,
                "fixture_mode": run.fixture_mode,
                "parameters": run.parameters,
                "error": run.error,
            },
            "steps": [
                {
                    "position": row.position,
                    "name": row.step_name,
                    "status": row.status,
                    "duration_seconds": row.duration_seconds,
                    "error": row.error,
                }
                for row in steps
            ],
            "artifacts": [
                {
                    "artifact_id": row.artifact_id,
                    "kind": row.kind,
                    "path": row.path,
                    "source_uri": row.source_uri,
                    "resolved_url": row.resolved_url,
                    "status_code": row.status_code,
                    "content_type": row.content_type,
                    "etag": row.etag,
                    "last_modified": row.last_modified,
                    "retrieved_at": row.retrieved_at.isoformat(),
                    "sha256": row.sha256,
                    "size_bytes": row.size_bytes,
                }
                for row in artifacts
            ],
            "events": [
                {
                    "type": row.event_type,
                    "timestamp": row.timestamp.isoformat(),
                    "step": row.step,
                    "level": row.level,
                    "metadata": row.metadata,
                }
                for row in events
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return

    metadata = Table(title=f"Run · {run.run_id[:8]}", show_header=False, box=None)
    metadata.add_column("Field", style="bold")
    metadata.add_column("Value")
    metadata.add_row("Run ID", run.run_id)
    metadata.add_row("Job", run.job_id)
    metadata.add_row("Version", run.job_version)
    metadata.add_row("Status", run.status)
    metadata.add_row("Started", run.started_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"))
    duration = f"{run.duration_seconds:.3f}s" if run.duration_seconds is not None else "—"
    metadata.add_row("Duration", duration)
    metadata.add_row("Error", run.error or "—")
    console.print(metadata)

    step_table = Table(title="Steps", show_header=True, header_style="bold")
    step_table.add_column("#", justify="right")
    step_table.add_column("Step")
    step_table.add_column("Status")
    step_table.add_column("Duration", justify="right")
    for row in steps:
        step_table.add_row(
            str(row.position),
            row.step_name,
            row.status,
            f"{row.duration_seconds:.3f}s",
        )
    console.print(step_table)

    artifact_table = Table(title="Artifacts", show_header=True, header_style="bold")
    artifact_table.add_column("Kind")
    artifact_table.add_column("Path")
    artifact_table.add_column("SHA-256")
    for row in artifacts:
        artifact_table.add_row(row.kind, row.path, row.sha256[:12] + "…")
    console.print(artifact_table)
    console.print(f"[dim]{len(events)} runtime event(s) persisted[/dim]")
