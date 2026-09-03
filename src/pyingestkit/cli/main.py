from __future__ import annotations

from .app import app


def main() -> None:
    """Console-script entry point."""
    app(prog_name="pyingest")


if __name__ == "__main__":
    main()
