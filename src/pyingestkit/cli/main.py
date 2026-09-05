from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from .app import app


def _load_local_dotenv() -> None:
    """Load only the working-directory .env without overriding OS variables."""

    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def main() -> None:
    """Console-script entry point."""
    _load_local_dotenv()
    app(prog_name="pyingest")


if __name__ == "__main__":
    main()
