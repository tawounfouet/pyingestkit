from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from rich.table import Table

from pyingestkit.cli.common import (
    artifact_store_or_exit,
    fail,
    metadata_store_or_exit,
    project_config_or_exit,
)
from pyingestkit.cli.console import console
from pyingestkit.core.exceptions import StorageError
from pyingestkit.metadata import DiffMetadataCapability


def status_command(
    run_id: Annotated[
        str | None,
        typer.Argument(help="Full run UUID or unique prefix. Defaults to the most recent run."),
    ] = None,
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
    """Inspect one persisted run, its artifacts, validations, and runtime events."""
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    store = metadata_store_or_exit(project_config, workspace=effective_workspace)
    if run_id is None:
        recent_runs = store.list_runs(limit=1)
        if not recent_runs:
            fail(
                "Missing argument 'run_id'. No ingestion runs found in metadata store.\n"
                "Execute a job first with 'pyingest run <job_id>'.",
                code=2,
            )
        run = recent_runs[0]
        if not json_output:
            console.print(
                f"[dim]No run ID specified. Showing most recent run: [bold cyan]{run.run_id[:8]}[/bold cyan] ({run.job_id})[/dim]\n"
            )
    else:
        try:
            run = store.get_run(run_id)
        except KeyError:
            fail(f"Unknown run: {run_id}", code=2)
        except ValueError as exc:
            fail(str(exc), code=2)
    steps = store.list_steps(run.run_id)
    artifacts = store.list_artifacts(run.run_id)
    validations = store.list_validations(run.run_id)
    events = store.list_events(run.run_id)
    diffs = (
        store.list_dataset_diffs(run.run_id) if isinstance(store, DiffMetadataCapability) else ()
    )

    reports: list[dict[str, object]] = []
    try:
        artifact_store = artifact_store_or_exit(project_config, workspace=effective_workspace)
        run_uuid = UUID(run.run_id)
        manifest_path = artifact_store.path_for(run.job_id, run_uuid, "manifest.json")
        if manifest_path.is_file():
            manifest_bytes = manifest_path.read_bytes()
        else:
            manifest_bytes = artifact_store.read_bytes(
                artifact_store.uri_for(run.job_id, run_uuid, "manifest.json")
            )
        manifest_payload = json.loads(manifest_bytes)
        raw_reports = manifest_payload.get("reports", [])
        if isinstance(raw_reports, list):
            reports = [report for report in raw_reports if isinstance(report, dict)]
    except (OSError, StorageError, ValueError, TypeError, json.JSONDecodeError):
        reports = []

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
                    "storage_uri": row.storage_uri,
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
            "validations": [
                {
                    "rule": row.rule,
                    "severity": row.severity,
                    "status": row.status,
                    "message": row.message,
                    "metadata": row.metadata,
                }
                for row in validations
            ],
            "reports": reports,
            "diffs": [
                {
                    "step": row.step_name,
                    "dataset_id": row.dataset_id,
                    "previous_version_id": row.previous_version_id,
                    "candidate_fingerprint": row.candidate_fingerprint,
                    "added_count": row.added_count,
                    "removed_count": row.removed_count,
                    "changed_count": row.changed_count,
                    "unchanged_count": row.unchanged_count,
                    "entries_truncated": row.entries_truncated,
                    "report_path": row.report_path,
                    "created_at": row.created_at.isoformat(),
                }
                for row in diffs
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
    for step_record in steps:
        step_table.add_row(
            str(step_record.position),
            step_record.step_name,
            step_record.status,
            f"{step_record.duration_seconds:.3f}s",
        )
    console.print(step_table)

    artifact_table = Table(title="Artifacts", show_header=True, header_style="bold")
    artifact_table.add_column("Kind")
    artifact_table.add_column("Path")
    artifact_table.add_column("SHA-256")
    for artifact_record in artifacts:
        artifact_table.add_row(
            artifact_record.kind, artifact_record.path, artifact_record.sha256[:12] + "…"
        )
    console.print(artifact_table)

    if validations:
        validation_table = Table(title="Validations", show_header=True, header_style="bold")
        validation_table.add_column("Rule")
        validation_table.add_column("Status")
        validation_table.add_column("Severity")
        validation_table.add_column("Message")
        for validation in validations:
            validation_table.add_row(
                validation.rule,
                validation.status,
                validation.severity,
                validation.message,
            )
        console.print(validation_table)

    if reports:
        report_table = Table(title="Run reports", show_header=True, header_style="bold")
        report_table.add_column("Kind")
        report_table.add_column("Path")
        report_table.add_column("Step")
        for report in reports:
            report_table.add_row(
                str(report.get("kind", "—")),
                str(report.get("path", "—")),
                str(report.get("step", "—")),
            )
        console.print(report_table)

    if diffs:
        diff_table = Table(title="Dataset diffs", show_header=True, header_style="bold")
        diff_table.add_column("Step")
        diff_table.add_column("Added", justify="right")
        diff_table.add_column("Removed", justify="right")
        diff_table.add_column("Changed", justify="right")
        diff_table.add_column("Unchanged", justify="right")
        diff_table.add_column("Report")
        for diff in diffs:
            diff_table.add_row(
                diff.step_name,
                str(diff.added_count),
                str(diff.removed_count),
                str(diff.changed_count),
                str(diff.unchanged_count),
                diff.report_path,
            )
        console.print(diff_table)

    console.print(f"[dim]{len(events)} runtime event(s) persisted[/dim]")
