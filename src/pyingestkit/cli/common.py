from __future__ import annotations

import json
from typing import Any, NoReturn

import typer

from pyingestkit.core.job import Job
from pyingestkit.core.registry import JobRegistry
from pyingestkit.plugins.discovery import load_registry

from .console import error_console


def get_registry() -> JobRegistry:
    """Load installed jobs through the explicit plugin discovery contract."""
    return load_registry()


def get_job_or_exit(registry: JobRegistry, job_id: str) -> Job:
    try:
        return registry.get(job_id)
    except KeyError:
        fail(f"Unknown ingestion job: {job_id}", code=2)


def parse_params_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        fail(f"--params-json must be valid JSON: {exc}", code=2)
    if not isinstance(parsed, dict):
        fail("--params-json must decode to a JSON object", code=2)
    return parsed


def fail(message: str, *, code: int = 1) -> NoReturn:
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=code)
