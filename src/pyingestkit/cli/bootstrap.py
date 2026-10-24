"""Dependency-light bootstrap for the PyIngestKit CLI."""

from __future__ import annotations

import errno
import importlib.util
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from pyingestkit.cli.exit_codes import ExitCode

CLI_DEPENDENCIES = ("typer", "rich")
MISSING_DEPENDENCY_EXIT_CODE = int(ExitCode.MISSING_OPTIONAL_DEPENDENCY)

_PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _missing_cli_dependencies() -> tuple[str, ...]:
    """Identify any missing dependencies required to run the CLI."""
    return tuple(dep for dep in CLI_DEPENDENCIES if importlib.util.find_spec(dep) is None)


def _selected_profile(root_env: Path) -> str | None:
    """Resolve PYINGEST_ENV from OS first, then from the root .env file if available."""
    value = os.getenv("PYINGEST_ENV")
    if value is None and root_env.is_file():
        try:
            from dotenv import dotenv_values

            raw = dotenv_values(root_env).get("PYINGEST_ENV")
            value = str(raw) if raw is not None else None
        except ImportError:
            pass

    if value is None:
        return None
    normalized = value.strip()
    if not normalized or not _PROFILE_NAME.fullmatch(normalized):
        return None
    return normalized


def _load_local_dotenv() -> None:
    """Load deterministic working-directory dotenv files without overriding OS variables.

    Precedence is ``OS environment > profile dotenv > root .env``.
    Checks in:
      1. cwd / 'infra' / 'envs' / f'.env.{profile}'
      2. cwd / 'envs' / f'.env.{profile}'
      3. cwd / f'.env.{profile}'
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    cwd = Path.cwd()
    root_env = cwd / ".env"
    profile = _selected_profile(root_env)
    if profile:
        candidates = (
            cwd / "infra" / "envs" / f".env.{profile}",
            cwd / "envs" / f".env.{profile}",
            cwd / f".env.{profile}",
        )
        for target in candidates:
            if target.is_file():
                load_dotenv(dotenv_path=target, override=False)
                break

    if root_env.is_file():
        load_dotenv(dotenv_path=root_env, override=False)


def _detect_prog_name(argv: Sequence[str] | None = None) -> str:
    """Determine the CLI program name from invocation or fallback to 'pik'."""
    raw = sys.argv[0] if argv is None and sys.argv else ""
    basename = Path(raw).name
    if basename in ("pik", "pyingest", "pyingestkit"):
        return basename
    return "pik"


def main(argv: Sequence[str] | None = None, prog_name: str | None = None) -> int:
    """Run PyIngestKit CLI with dependency guards and signal handling."""
    missing = _missing_cli_dependencies()
    if missing:
        deps = ", ".join(missing)
        print(
            f"PyIngestKit CLI dependencies missing: {deps}.\n"
            'Install CLI dependencies via: pip install "pyingestkit[cli]" '
            "or pip install typer rich",
            file=sys.stderr,
        )
        return MISSING_DEPENDENCY_EXIT_CODE

    # Load local environment configuration
    _load_local_dotenv()

    # Dynamic import of heavy Typer application
    from pyingestkit.cli.app import app

    resolved_prog = prog_name or _detect_prog_name(argv)
    args = list(argv) if argv is not None else None

    try:
        app(args=args, prog_name=resolved_prog, standalone_mode=True)
    except BrokenPipeError:
        if "PYTEST_CURRENT_TEST" not in os.environ:
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                try:
                    os.dup2(devnull, sys.stdout.fileno())
                finally:
                    os.close(devnull)
            except (OSError, ValueError):
                pass
        return int(ExitCode.BROKEN_PIPE)
    except OSError as exc:
        if exc.errno == errno.EPIPE:
            return int(ExitCode.BROKEN_PIPE)
        raise
    except KeyboardInterrupt:
        return int(ExitCode.INTERRUPTED)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return int(ExitCode.SUCCESS)
        if isinstance(code, int):
            return code
        return int(ExitCode.GENERAL_ERROR)

    return int(ExitCode.SUCCESS)


__all__ = ["CLI_DEPENDENCIES", "MISSING_DEPENDENCY_EXIT_CODE", "main"]
