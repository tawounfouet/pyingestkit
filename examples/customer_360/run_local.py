"""Run the installed-package Customer 360 local reference profile."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app import read_customer_mart, run_customer_360


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pyingestkit-customer360-") as directory:
        evidence = run_customer_360(workspace=Path(directory), engine_id="pandas")
        rows = [
            dict(record.fields)
            for record in read_customer_mart(evidence).records
        ]
        print(
            json.dumps(
                {
                    "dataset_id": evidence.customer_mart_version.dataset_id,
                    "version_id": evidence.customer_mart_version.version_id,
                    "transformation_execution_id": evidence.transformation_execution_id,
                    "replay_run_id": str(evidence.replay.replay_run_id),
                    "source_run_id": str(evidence.replay.source_run_id),
                    "row_count": len(rows),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
