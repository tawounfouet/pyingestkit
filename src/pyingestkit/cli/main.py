from __future__ import annotations

import sys

from pyingestkit.cli.bootstrap import main as bootstrap_main


def main() -> None:
    """Console-script entry point delegating to guarded bootstrap."""
    sys.exit(bootstrap_main(prog_name="pyingest"))


if __name__ == "__main__":
    main()
