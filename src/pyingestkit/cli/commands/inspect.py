from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from pyingestkit.cli.common import fail, get_job_or_exit, get_registry
from pyingestkit.cli.console import console


def inspect_command(
    job_id: Annotated[
        str | None,
        typer.Argument(help="Namespaced ingestion job ID to inspect."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of Rich output."),
    ] = False,
) -> None:
    """Inspect an installed ingestion job."""
    if not job_id:
        registry = get_registry()
        jobs = sorted(registry.list(), key=lambda j: j.id)
        if jobs:
            job_list = "\n".join(f"  • {j.id} (v{j.version})" for j in jobs)
            fail(
                f"Missing argument 'job_id'. Please specify a job ID to inspect.\n\n"
                f"Installed jobs:\n{job_list}\n\n"
                f"Usage: pyingest inspect <job_id>",
                code=2,
            )
        else:
            fail("Missing argument 'job_id'. No ingestion jobs currently installed.", code=2)

    job = get_job_or_exit(get_registry(), job_id)
    payload = {
        "id": job.id,
        "version": job.version,
        "description": job.description,
        "depends_on": list(job.depends_on),
        "requires_artifacts": job.requires_artifacts,
        "requires_metadata": job.requires_metadata,
        "steps": [step.step_name for step in job.pipeline()],
    }

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return

    metadata = Table(title=f"Job · {job.id}", show_header=False, box=None)
    metadata.add_column("Field", style="bold")
    metadata.add_column("Value")
    metadata.add_row("Version", job.version)
    metadata.add_row("Description", job.description or "—")
    metadata.add_row("Dependencies", ", ".join(job.depends_on) if job.depends_on else "—")
    metadata.add_row("Required Artifacts", job.requires_artifacts or "Any")
    metadata.add_row("Required Metadata", job.requires_metadata or "Any")
    console.print(metadata)

    steps = Table(title="Pipeline", show_header=True, header_style="bold")
    steps.add_column("#", justify="right")
    steps.add_column("Step")
    for index, step in enumerate(job.pipeline(), start=1):
        steps.add_row(str(index), step.step_name)
    console.print(steps)
