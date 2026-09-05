from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse

import typer
from rich.table import Table

from pyingestkit.cli.common import project_config_or_exit
from pyingestkit.cli.console import console
from pyingestkit.config.loader import resolve_config_path_with_source
from pyingestkit.config.models import (
    ArtifactBackend,
    MetadataBackend,
    PyIngestKitConfig,
)


def _mask_url(url: str | None) -> str | None:
    if not url:
        return url
    try:
        parsed = urlparse(url)
        if parsed.password:
            user = parsed.username or ""
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            netloc = f"{user}:******@{host}{port}"
            return urlunparse(parsed._replace(netloc=netloc))
        return url
    except Exception:
        return re.sub(r":([^/@]+)@", r":******@", url)


def config_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to YAML configuration file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", "-w", help="Workspace directory override."),
    ] = None,
    show_secrets: Annotated[
        bool,
        typer.Option("--show-secrets", help="Display credentials and database passwords unmasked."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Show active configuration, resolved source, and backend settings."""
    resolved_path, resolution_method = resolve_config_path_with_source(config)
    project_config: PyIngestKitConfig = project_config_or_exit(config)

    effective_workspace = workspace or project_config.runtime.workspace
    active_env = os.getenv("PYINGEST_ENV")

    # Artifacts resolution
    artifacts_backend = project_config.artifacts.backend.value
    s3_config = project_config.artifacts.s3
    s3_endpoint = (
        os.getenv(s3_config.endpoint_url_env)
        if s3_config.endpoint_url_env
        else None
    )

    # Metadata resolution
    metadata_backend = project_config.metadata.backend.value
    sqlite_path = (
        project_config.metadata.sqlite.path
        or (Path(effective_workspace) / "state" / "pyingest.sqlite3")
    )
    postgres_dsn_env = project_config.metadata.postgres.dsn_env
    raw_postgres_dsn = os.getenv(postgres_dsn_env)
    postgres_dsn = raw_postgres_dsn if show_secrets else _mask_url(raw_postgres_dsn)

    # Targets resolution
    targets_info: list[dict[str, object]] = []
    for target_key, target in project_config.targets.items():
        raw_target_dsn = os.getenv(target.dsn_env)
        target_dsn = raw_target_dsn if show_secrets else _mask_url(raw_target_dsn)
        targets_info.append(
            {
                "id": target.target_id,
                "type": target.type,
                "schema": target.schema_name,
                "table": target.table,
                "load_mode": target.load_mode,
                "dsn_env": target.dsn_env,
                "dsn_set": raw_target_dsn is not None,
                "dsn": target_dsn,
            }
        )

    if json_output:
        payload = {
            "source": {
                "path": str(resolved_path) if resolved_path else None,
                "resolution": resolution_method,
                "environment": active_env,
            },
            "runtime": {
                "workspace": str(effective_workspace),
                "fixture_mode": project_config.runtime.fixture_mode,
                "parameters": project_config.runtime.parameters,
            },
            "artifacts": {
                "backend": artifacts_backend,
                "local_root": str(effective_workspace) if artifacts_backend == ArtifactBackend.LOCAL.value else None,
                "s3": {
                    "bucket": s3_config.bucket,
                    "prefix": s3_config.prefix,
                    "region": s3_config.region_name,
                    "endpoint_url": s3_endpoint,
                    "endpoint_url_env": s3_config.endpoint_url_env,
                    "cache_path": str(s3_config.cache_path) if s3_config.cache_path else None,
                }
                if artifacts_backend == ArtifactBackend.S3.value
                else None,
            },
            "metadata": {
                "backend": metadata_backend,
                "sqlite": {
                    "path": str(sqlite_path),
                    "exists": sqlite_path.exists(),
                }
                if metadata_backend == MetadataBackend.SQLITE.value
                else None,
                "postgres": {
                    "dsn_env": postgres_dsn_env,
                    "dsn_set": raw_postgres_dsn is not None,
                    "dsn": postgres_dsn,
                }
                if metadata_backend == MetadataBackend.POSTGRES.value
                else None,
            },
            "targets": targets_info,
            "logging": {
                "level": project_config.logging.level,
                "format": project_config.logging.format.value,
                "console": project_config.logging.console,
                "file": {
                    "enabled": project_config.logging.file.enabled,
                    "path": str(project_config.logging.file.path),
                    "level": project_config.logging.file.level,
                },
            },
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2 if show_secrets else None))
        return

    # Render Rich console view
    table = Table(title="PyIngestKit Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="bold", width=22)
    table.add_column("Setting", style="dim", width=22)
    table.add_column("Value")

    # Source & Environment
    table.add_row("Resolution", "Config File", str(resolved_path) if resolved_path else "[dim]None (in-memory defaults)[/dim]")
    table.add_row("", "Origin", f"[green]{resolution_method}[/green]")
    table.add_row("", "Environment (PYINGEST_ENV)", active_env or "[dim]—[/dim]")
    table.add_row("", "Workspace", str(Path(effective_workspace).resolve()))
    table.add_row("", "Fixture Mode", str(project_config.runtime.fixture_mode))

    # Artifacts
    table.add_section()
    table.add_row("Artifacts", "Backend", f"[bold]{artifacts_backend.upper()}[/bold]")
    if artifacts_backend == ArtifactBackend.LOCAL.value:
        table.add_row("", "Storage Root", str(effective_workspace))
    else:
        table.add_row("", "Bucket", s3_config.bucket or "[red]Not configured[/red]")
        table.add_row("", "Prefix", s3_config.prefix)
        table.add_row("", "Region", s3_config.region_name or "[dim]auto[/dim]")
        table.add_row("", "Endpoint URL", s3_endpoint or "[dim]AWS Default[/dim]")
        if s3_config.cache_path:
            table.add_row("", "Cache Path", str(s3_config.cache_path))

    # Metadata
    table.add_section()
    table.add_row("Metadata", "Backend", f"[bold]{metadata_backend.upper()}[/bold]")
    if metadata_backend == MetadataBackend.SQLITE.value:
        status = "[green]exists[/green]" if sqlite_path.exists() else "[dim]not created yet[/dim]"
        table.add_row("", "Database Path", f"{sqlite_path} ({status})")
    else:
        dsn_display = postgres_dsn or f"[bold red]UNSET[/bold red] (set {postgres_dsn_env})"
        table.add_row("", "DSN Env Variable", postgres_dsn_env)
        table.add_row("", "Resolved DSN", dsn_display)

    # Targets
    if targets_info:
        table.add_section()
        for idx, t in enumerate(targets_info):
            cat = "Targets" if idx == 0 else ""
            table.add_row(cat, f"[{t['id']}] Table", f"{t['schema']}.{t['table']} ({t['load_mode']})")
            table.add_row("", f"[{t['id']}] DSN", str(t['dsn']) if t['dsn_set'] else f"[bold red]UNSET[/bold red] ({t['dsn_env']})")

    # Logging
    table.add_section()
    table.add_row("Logging", "Level / Format", f"{project_config.logging.level} / {project_config.logging.format.value}")
    if project_config.logging.file.enabled:
        table.add_row("", "File Log", f"{project_config.logging.file.path} ({project_config.logging.file.level})")

    console.print(table)
