from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from pyingestkit.cli.common import get_job_or_exit, get_registry
from pyingestkit.cli.console import console


def inspect_command(
    job_id: Annotated[str, typer.Argument(help="Namespaced ingestion job ID to inspect.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """Inspect an installed ingestion job."""
    job = get_job_or_exit(get_registry(), job_id)
    payload = {
        "id": job.id,
        "version": job.version,
        "description": job.description,
        "depends_on": list(job.depends_on),
        "steps": [step.step_name for step in job.pipeline()],
    }

    if json_output:
        console.print_json(json.dumps(payload))
        return

    metadata = Table(title=f"Job · {job.id}", show_header=False, box=None)
    metadata.add_column("Field", style="bold")
    metadata.add_column("Value")
    metadata.add_row("Version", job.version)
    metadata.add_row("Description", job.description or "—")
    metadata.add_row("Dependencies", ", ".join(job.depends_on) if job.depends_on else "—")
    console.print(metadata)

    steps = Table(title="Pipeline", show_header=True, header_style="bold")
    steps.add_column("#", justify="right")
    steps.add_column("Step")
    for index, step in enumerate(job.pipeline(), start=1):
        steps.add_row(str(index), step.step_name)
    console.print(steps)
