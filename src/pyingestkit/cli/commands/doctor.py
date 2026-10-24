"""System environment and dependencies diagnostics command for PyIngestKit CLI."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from pyingestkit import __version__
from pyingestkit.cli.console import console
from pyingestkit.cli.exit_codes import ExitCode
from pyingestkit.cli.security import redact_sensitive_text


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: str  # "OK", "MISSING", "WARNING"
    installed_version: str | None
    required: bool
    details: str | None = None


@dataclass(frozen=True, slots=True)
class DoctorReport:
    pyingestkit_version: str
    python_version: str
    python_supported: bool
    platform: str
    workspace_root: str
    active_profile: str | None
    active_config: str | None
    core_dependencies: tuple[CheckResult, ...]
    optional_extras: tuple[CheckResult, ...]

    def is_healthy(self) -> bool:
        if not self.python_supported:
            return False
        return all(c.status == "OK" for c in self.core_dependencies if c.required)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "healthy" if self.is_healthy() else "unhealthy",
            "pyingestkit": {
                "version": self.pyingestkit_version,
            },
            "runtime": {
                "python_version": self.python_version,
                "python_supported": self.python_supported,
                "platform": self.platform,
            },
            "environment": {
                "workspace_root": self.workspace_root,
                "active_profile": self.active_profile,
                "active_config": self.active_config,
            },
            "core_dependencies": [asdict(c) for c in self.core_dependencies],
            "optional_extras": [asdict(c) for c in self.optional_extras],
        }


def _check_module(
    module_name: str,
    distribution_name: str,
    *,
    required: bool = True,
    extra_label: str | None = None,
) -> CheckResult:
    spec = importlib.util.find_spec(module_name)
    display_name = f"{distribution_name} ({extra_label})" if extra_label else distribution_name
    if spec is None:
        status = "MISSING" if required else "WARNING"
        return CheckResult(
            name=display_name,
            status=status,
            installed_version=None,
            required=required,
            details=f"Module '{module_name}' is not installed",
        )

    try:
        dist_version = importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        dist_version = "installed (metadata unavailable)"

    return CheckResult(
        name=display_name,
        status="OK",
        installed_version=dist_version,
        required=required,
        details=None,
    )


def collect_doctor_report(workspace: Path | None = None) -> DoctorReport:
    ws = (workspace or Path.cwd()).resolve()
    py_version = platform.python_version()
    py_supported = sys.version_info >= (3, 11)

    core_deps = (
        _check_module("pydantic", "pydantic", required=True),
        _check_module("yaml", "PyYAML", required=True),
        _check_module("dotenv", "python-dotenv", required=True),
    )

    optional_extras = (
        _check_module("typer", "typer", required=True, extra_label="cli"),
        _check_module("rich", "rich", required=True, extra_label="cli"),
        _check_module("sqlalchemy", "SQLAlchemy", required=False, extra_label="postgres"),
        _check_module("psycopg", "psycopg", required=False, extra_label="postgres"),
        _check_module("boto3", "boto3", required=False, extra_label="s3"),
        _check_module("httpx", "httpx", required=False, extra_label="http"),
        _check_module("pyarrow", "pyarrow", required=False, extra_label="parquet"),
        _check_module("openpyxl", "openpyxl", required=False, extra_label="excel"),
    )

    active_profile = os.getenv("PYINGEST_ENV")
    active_config = os.getenv("PYINGEST_CONFIG")
    if not active_config:
        for candidate in ("pyingest.yml", "pyingestkit.yml", ".pyingest.yml"):
            target = ws / candidate
            if target.is_file():
                active_config = candidate
                break

    return DoctorReport(
        pyingestkit_version=__version__,
        python_version=py_version,
        python_supported=py_supported,
        platform=platform.platform(),
        workspace_root=str(ws),
        active_profile=active_profile,
        active_config=active_config,
        core_dependencies=core_deps,
        optional_extras=optional_extras,
    )


def render_human_doctor(report: DoctorReport) -> None:
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]PyIngestKit Doctor[/bold cyan] [dim]v{report.pyingestkit_version}[/dim]\n"
            f"Python {report.python_version} on {report.platform}",
            border_style="cyan",
        )
    )

    # Core dependencies
    core_table = Table(title="Core Runtime Dependencies", show_header=True, header_style="bold")
    core_table.add_column("Component")
    core_table.add_column("Status", justify="center")
    core_table.add_column("Version", justify="right")

    for dep in report.core_dependencies:
        if dep.status == "OK":
            status_text = "[bold green]✓ OK[/bold green]"
            version_text = f"[green]{dep.installed_version}[/green]"
        else:
            status_text = "[bold red]✗ MISSING[/bold red]"
            version_text = "[dim]-[/dim]"
        core_table.add_row(dep.name, status_text, version_text)

    console.print(core_table)
    console.print()

    # Optional extras
    extras_table = Table(title="Optional Provider Extras", show_header=True, header_style="bold")
    extras_table.add_column("Extra / Dependency")
    extras_table.add_column("Status", justify="center")
    extras_table.add_column("Version", justify="right")

    for dep in report.optional_extras:
        if dep.status == "OK":
            status_text = "[bold green]✓ OK[/bold green]"
            version_text = f"[green]{dep.installed_version}[/green]"
        else:
            status_text = "[bold yellow]! OPTIONAL[/bold yellow]"
            version_text = "[dim]not installed[/dim]"
        extras_table.add_row(dep.name, status_text, version_text)

    console.print(extras_table)
    console.print()

    # Environment
    env_table = Table(title="Workspace & Environment", show_header=True, header_style="bold")
    env_table.add_column("Setting")
    env_table.add_column("Value")

    env_table.add_row("Workspace Root", report.workspace_root)
    env_table.add_row("Active Profile", report.active_profile or "[dim]none (default)[/dim]")
    env_table.add_row("Active Config", report.active_config or "[dim]none detected[/dim]")
    console.print(env_table)
    console.print()

    if report.is_healthy():
        console.print("[bold green]✓ PyIngestKit environment is healthy.[/bold green]\n")
    else:
        console.print(
            "[bold red]✗ Some required components or Python version are unsupported.[/bold red]\n"
        )


def doctor_command(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit raw JSON machine contract to stdout."),
    ] = False,
) -> None:
    """Run side-effect-free environment and dependencies diagnostics."""
    report = collect_doctor_report()

    if json_output:
        raw_json = json.dumps(report.to_dict(), indent=2)
        sanitized = redact_sensitive_text(raw_json)
        typer.echo(sanitized)
    else:
        render_human_doctor(report)

    if not report.is_healthy():
        raise typer.Exit(code=int(ExitCode.GENERAL_ERROR))


__all__ = ["CheckResult", "DoctorReport", "collect_doctor_report", "doctor_command"]
