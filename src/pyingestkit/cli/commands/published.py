from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pyingestkit.cli.console import console
from pyingestkit.versioning import FilesystemDatasetVersionStore


def published_command(
    dataset_id: Annotated[str, typer.Argument(help="Logical dataset identifier")],
    workspace: Annotated[Path, typer.Option("--workspace", "-w")] = Path(".pyingest"),
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    published = FilesystemDatasetVersionStore(workspace).get_published(dataset_id)
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
