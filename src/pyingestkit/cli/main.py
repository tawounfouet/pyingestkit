from __future__ import annotations

from dotenv import load_dotenv

from .app import app


def main() -> None:
    """Console-script entry point."""
    load_dotenv()
    app(prog_name="pyingest")


if __name__ == "__main__":
    main()
