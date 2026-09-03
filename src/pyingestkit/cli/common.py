from __future__ import annotations

import json
from typing import Any, NoReturn

import typer
import yaml

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


def parse_param_assignments(values: list[str] | None) -> dict[str, Any]:
    """Parse repeated ``KEY=VALUE`` options using YAML scalar semantics."""
    parsed: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            fail(f"--param must use KEY=VALUE syntax, got: {item!r}", code=2)
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            fail("--param key cannot be empty", code=2)
        try:
            value = yaml.safe_load(raw_value)
        except yaml.YAMLError as exc:
            fail(f"Invalid value for --param {key}: {exc}", code=2)
        parsed[key] = value
    return parsed


def fail(message: str, *, code: int = 1) -> NoReturn:
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=code)
