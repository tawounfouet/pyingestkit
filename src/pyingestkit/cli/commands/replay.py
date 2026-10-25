from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit.adapters.filesystem import (
    FileArtifactStore,
    FileConditionalDatasetPublisher,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.formats.csv import CsvDecoder
from pyingestkit.adapters.formats.json import JsonDecoder
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.replay import ReplayServiceV2
from pyingestkit.application.resolver import DefaultReplayProvenanceResolver
from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.application.sources import SourceRegistry
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
from pyingestkit.domain.artifacts import ArtifactIntegrityError
from pyingestkit.domain.governance import ConditionalPublicationStatus
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner


def replay_command(
    source_run_id: Annotated[
        str | None,
        typer.Argument(help="Historical run ID or unique prefix. Defaults to the most recent run."),
    ] = None,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", exists=True, dir_okay=False)
    ] = None,
    workspace: Annotated[Path | None, typer.Option("--workspace", "-w")] = None,
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
    allow_version_change: Annotated[bool, typer.Option("--allow-version-change")] = False,
    no_verify: Annotated[bool, typer.Option("--no-verify")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    dataset: Annotated[
        str | None,
        typer.Option(
            "--dataset", "-d", help="Logical dataset identifier for V2 provenance replay."
        ),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option(
            "--version", "-v", help="Dataset version ID to replay from durable provenance."
        ),
    ] = None,
    publish: Annotated[
        bool,
        typer.Option("--publish", help="Publish the replayed dataset version using governed CAS."),
    ] = False,
) -> None:
    project_config = project_config_or_exit(config)
    effective_workspace = workspace or project_config.runtime.workspace
    overrides = dict(project_config.runtime.parameters)
    overrides.update(parse_param_assignments(param))

    # V2 Dataset Provenance Replay Path
    if dataset is not None or version is not None:
        if dataset is None:
            fail(
                "Missing option '--dataset' / '-d'. Specifying --version requires --dataset.",
                code=2,
            )

        artifact_store = FileArtifactStore(root=effective_workspace)
        version_store = FileDatasetVersionStore(root=effective_workspace)
        ledger = MemoryPublicationLedger()

        if version is not None:
            target_version = version
        else:
            published = version_store.get_published(dataset)
            if published is not None:
                target_version = published.version_id
            else:
                versions = version_store.list(dataset)
                if not versions:
                    fail(
                        f"No versions found for dataset '{dataset}' in workspace {effective_workspace}.",
                        code=1,
                    )
                target_version = versions[0].version_id

        decoders = DecoderRegistry()
        decoders.register(JsonDecoder())
        decoders.register(CsvDecoder())
        sources = SourceRegistry()
        runtime = IngestionRuntime(
            sources=sources,
            decoders=decoders,
            artifacts=artifact_store,
            versions=version_store,
            publisher=version_store,
        )
        service = ReplayServiceV2(
            runtime=runtime,
            ledger=ledger,
        )
        resolver = DefaultReplayProvenanceResolver(
            version_store=version_store,
            artifact_store=artifact_store,
        )

        try:
            request = resolver.resolve_from_version(
                dataset_id=dataset,
                version_id=target_version,
                parameter_overrides=overrides,
            )
        except (KeyError, LookupError, ValueError, OSError) as exc:
            fail(
                f"Failed to resolve replay provenance for {dataset}@{target_version}: {exc}",
                code=1,
            )

        try:
            result = service.replay(request)
        except (ArtifactIntegrityError, ReplayError, ValueError, OSError) as exc:
            fail(f"Replay execution failed: {exc}", code=1)

        publication_outcome = None
        if publish:
            if not result.succeeded:
                fail("Cannot publish an unsuccessful replay result.", code=1)
            publisher = FileConditionalDatasetPublisher(store=version_store, ledger=ledger)
            try:
                publication_outcome = service.publish_replay(result, publisher=publisher)
            except (ValueError, OSError, RuntimeError) as exc:
                fail(f"CAS publication failed: {exc}", code=1)

        if json_output:
            payload = {
                "source_run_id": str(result.source_run_id),
                "replay_run_id": str(result.replay_run_id),
                "dataset_id": result.lineage.dataset_id if result.lineage else dataset,
                "version_id": result.lineage.version_id if result.lineage else target_version,
                "matched": result.matched,
                "succeeded": result.succeeded,
                "published": (
                    publication_outcome is not None
                    and publication_outcome.status is ConditionalPublicationStatus.SUCCEEDED
                ),
                "origin_raw_checksum": result.lineage.origin_raw_checksum if result.lineage else "",
                "replay_raw_checksum": result.lineage.replay_raw_checksum if result.lineage else "",
                "lineage_id": result.lineage.lineage_id if result.lineage else None,
            }
            if publication_outcome is not None:
                payload["publication_operation_id"] = str(publication_outcome.intent.operation_id)
                payload["publication_status"] = publication_outcome.status.value
                payload["revision"] = (
                    publication_outcome.snapshot.revision.value
                    if publication_outcome.snapshot and publication_outcome.snapshot.revision
                    else None
                )
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        else:
            table = Table(show_header=False, box=None)
            table.add_row("[bold]Dataset:[/bold]", dataset)
            table.add_row("[bold]Target Version:[/bold]", target_version)
            table.add_row("[bold]Source Run ID:[/bold]", str(result.source_run_id))
            table.add_row("[bold]Replay Run ID:[/bold]", f"[cyan]{result.replay_run_id}[/cyan]")
            integrity_str = (
                "[bold green]MATCHED[/bold green]"
                if result.matched
                else "[bold red]MISMATCH[/bold red]"
            )
            table.add_row("[bold]RAW Integrity:[/bold]", integrity_str)
            if result.lineage:
                table.add_row("[bold]Lineage ID:[/bold]", result.lineage.lineage_id)
            if publication_outcome is not None:
                pub_status = (
                    f"[bold green]{publication_outcome.status.value.upper()}[/bold green]"
                    if publication_outcome.status is ConditionalPublicationStatus.SUCCEEDED
                    else f"[bold red]{publication_outcome.status.value.upper()}[/bold red]"
                )
                rev = (
                    publication_outcome.snapshot.revision.value
                    if publication_outcome.snapshot and publication_outcome.snapshot.revision
                    else "N/A"
                )
                table.add_row("[bold]CAS Publication:[/bold]", f"{pub_status} (rev: {rev})")
            console.print(
                Panel(table, title="[bold green]Replay Provenance Execution[/bold green]")
            )

        if not result.succeeded:
            raise typer.Exit(code=1)
        return

    # V1 Replay Service Legacy Path
    metadata = metadata_store_or_exit(project_config, workspace=effective_workspace)
    artifact_store_v1 = artifact_store_or_exit(project_config, workspace=effective_workspace)
    runner = Runner(artifact_store_v1, metadata_store=metadata)
    service_v1 = ReplayService(runner, get_registry())

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
        result_v1 = service_v1.replay(
            target_run_id,
            parameters=overrides,
            allow_version_change=allow_version_change,
            verify=not no_verify,
        )
    except ReplayMismatchError as exc:
        fail(f"{exc} (replay run_id={exc.run_id})", code=1)
    except ReplayError as exc:
        fail(str(exc), code=1)
    payload_v1 = {
        "run_id": result_v1.run.run_id,
        "source_run_id": result_v1.source_run_id,
        "job_id": result_v1.run.job_id,
        "source_job_version": result_v1.source_job_version,
        "executed_job_version": result_v1.executed_job_version,
        "verification_mode": result_v1.verification_mode,
        "expected_fingerprint": result_v1.expected_fingerprint,
        "actual_fingerprint": result_v1.actual_fingerprint,
        "matched": result_v1.matched,
        "status": result_v1.run.status.value,
    }
    if json_output:
        typer.echo(json.dumps(payload_v1, ensure_ascii=False, sort_keys=True))
    else:
        console.print(f"Replay run: [bold]{result_v1.run.run_id}[/bold]")
        console.print(f"Source run: {result_v1.source_run_id}")
        console.print(f"Verification: {result_v1.verification_mode} matched={result_v1.matched}")
    if not result_v1.run.succeeded:
        raise typer.Exit(code=1)
