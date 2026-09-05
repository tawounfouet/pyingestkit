from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from .app import app

_PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _selected_profile(root_env: Path) -> str | None:
    """Resolve PYINGEST_ENV from OS first, then the local root .env file."""

    value = os.getenv("PYINGEST_ENV")
    if value is None and root_env.is_file():
        raw = dotenv_values(root_env).get("PYINGEST_ENV")
        value = str(raw) if raw is not None else None
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or not _PROFILE_NAME.fullmatch(normalized):
        return None
    return normalized


def _load_local_dotenv() -> None:
    """Load deterministic working-directory dotenv files without overriding OS variables.

    Precedence is ``OS environment > profile dotenv > root .env``. Files ending in
    ``.example`` are documentation templates and are never loaded at runtime.
    """

    cwd = Path.cwd()
    root_env = cwd / ".env"
    profile = _selected_profile(root_env)
    if profile:
        candidates = (
            cwd / "envs" / f".env.{profile}",
            cwd / f".env.{profile}",
        )
        for target in candidates:
            if target.is_file():
                load_dotenv(dotenv_path=target, override=False)
                break

    load_dotenv(dotenv_path=root_env, override=False)


def main() -> None:
    """Console-script entry point."""

    _load_local_dotenv()
    app(prog_name="pyingest")


if __name__ == "__main__":
    main()
