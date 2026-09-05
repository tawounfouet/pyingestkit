from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pyingestkit.cli.common import dataset_version_store_or_exit, project_config_or_exit
from pyingestkit.cli.console import console


def versions_command(
    dataset_id: Annotated[str, typer.Argument(help="Logical dataset identifier")],
    config: Annotated[
        Path | None, typer.Option("--config", "-c", exists=True, dir_okay=False)
    ] = None,
    workspace: Annotated[Path | None, typer.Option("--workspace", "-w")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    store = dataset_version_store_or_exit(project_config, workspace=effective_workspace)
    rows = store.list_versions(dataset_id)
    if as_json:
        typer.echo(
            json.dumps(
                [
                    {
                        "dataset_id": row.dataset_id,
                        "version_id": row.version_id,
                        "fingerprint": row.fingerprint.id,
                        "snapshot_uri": row.snapshot_uri,
                        "created_at": row.created_at.isoformat(),
                        "created_from_run_id": row.created_from_run_id,
                        "job_id": row.job_id,
                        "job_version": row.job_version,
                    }
                    for row in rows
                ],
                indent=2,
                sort_keys=True,
            )
        )
        return
    table = Table(title=f"Dataset versions — {dataset_id}")
    table.add_column("Version")
    table.add_column("Created")
    table.add_column("Run")
    table.add_column("Job version")
    for row in rows:
        table.add_row(
            row.version_id, row.created_at.isoformat(), row.created_from_run_id, row.job_version
        )
    console.print(table)
