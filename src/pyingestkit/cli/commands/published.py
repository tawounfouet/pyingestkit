from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pyingestkit.cli.common import dataset_version_store_or_exit, project_config_or_exit
from pyingestkit.cli.console import console


def published_command(
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
    published = store.get_published(dataset_id)
    if published is None:
        raise typer.Exit(code=1)
    payload = {
        "dataset_id": published.dataset_id,
        "version_id": published.version_id,
        "fingerprint": published.fingerprint.id,
        "snapshot_uri": published.snapshot_uri,
        "published_at": published.published_at.isoformat(),
        "published_from_run_id": published.published_from_run_id,
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    console.print(f"[bold]{published.dataset_id}[/bold] → {published.version_id}")
    console.print(f"Snapshot: {published.snapshot_uri}")
    console.print(f"Published: {published.published_at.isoformat()}")
