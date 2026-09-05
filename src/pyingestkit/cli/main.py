from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from .app import app


def _load_local_dotenv() -> None:
    """Load the working-directory environment file without overriding OS variables."""
    import os

    env_name = os.getenv("PYINGEST_ENV")
    if env_name and env_name.strip():
        name = env_name.strip()
        candidates = (
            Path.cwd() / "envs" / f".env.{name}",
            Path.cwd() / "envs" / f".env.{name}.example",
            Path.cwd() / f".env.{name}",
        )
        for target in candidates:
            if target.exists():
                load_dotenv(dotenv_path=target, override=False)
                break

    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def main() -> None:
    """Console-script entry point."""
    _load_local_dotenv()
    app(prog_name="pyingest")


if __name__ == "__main__":
    main()
