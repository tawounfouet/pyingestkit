from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pyingestkit.cli.common import (
    artifact_store_or_exit,
    fail,
    get_registry,
    metadata_store_or_exit,
    parse_param_assignments,
    project_config_or_exit,
)
from pyingestkit.cli.console import console
from pyingestkit.core.exceptions import ReplayError, ReplayMismatchError
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner


def replay_command(
    source_run_id: Annotated[
        str | None,
        typer.Argument(
            help="Historical run ID or unique prefix. Defaults to the most recent run."
        ),
    ] = None,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", exists=True, dir_okay=False)
    ] = None,
    workspace: Annotated[Path | None, typer.Option("--workspace", "-w")] = None,
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
    allow_version_change: Annotated[bool, typer.Option("--allow-version-change")] = False,
    no_verify: Annotated[bool, typer.Option("--no-verify")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    metadata = metadata_store_or_exit(project_config, workspace=effective_workspace)
    artifact_store = artifact_store_or_exit(project_config, workspace=effective_workspace)
    runner = Runner(artifact_store, metadata_store=metadata)
    service = ReplayService(runner, get_registry())
    overrides = dict(project_config.runtime.parameters)
    overrides.update(parse_param_assignments(param))

    if source_run_id is None:
        recent_runs = metadata.list_runs(limit=1)
        if not recent_runs:
            fail(
                "Missing argument 'source_run_id'. No historical runs found in metadata store.\n"
                "Execute a job first with 'pyingest run <job_id>'.",
                code=2,
            )
        target_run_id = recent_runs[0].run_id
        if not json_output:
            console.print(
                f"[dim]No run ID specified. Replaying most recent run: [bold cyan]{target_run_id[:8]}[/bold cyan] ({recent_runs[0].job_id})[/dim]\n"
            )
    else:
        target_run_id = source_run_id

    try:
        result = service.replay(
            target_run_id,
            parameters=overrides,
            allow_version_change=allow_version_change,
            verify=not no_verify,
        )
    except ReplayMismatchError as exc:
        fail(f"{exc} (replay run_id={exc.run_id})", code=1)
    except ReplayError as exc:
        fail(str(exc), code=1)
    payload = {
        "run_id": result.run.run_id,
        "source_run_id": result.source_run_id,
        "job_id": result.run.job_id,
        "source_job_version": result.source_job_version,
        "executed_job_version": result.executed_job_version,
        "verification_mode": result.verification_mode,
        "expected_fingerprint": result.expected_fingerprint,
        "actual_fingerprint": result.actual_fingerprint,
        "matched": result.matched,
        "status": result.run.status.value,
    }
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        console.print(f"Replay run: [bold]{result.run.run_id}[/bold]")
        console.print(f"Source run: {result.source_run_id}")
        console.print(f"Verification: {result.verification_mode} matched={result.matched}")
    if not result.run.succeeded:
        raise typer.Exit(code=1)
