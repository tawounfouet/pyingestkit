from __future__ import annotations

import argparse
import os
import time

from sqlalchemy import create_engine

from pyingestkit import Dataset
from pyingestkit.targets import PostgresTarget, TargetLoadRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual PostgreSQL COPY baseline for PyIngestKit A2")
    parser.add_argument("--rows", type=int, default=100_000)
    args = parser.parse_args()
    dsn = os.environ.get("PYINGEST_TEST_POSTGRES_DSN")
    if not dsn:
        raise SystemExit("PYINGEST_TEST_POSTGRES_DSN is required")

    engine = create_engine(dsn, future=True)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS pyingest_copy_benchmark")
        connection.exec_driver_sql(
            "CREATE TABLE pyingest_copy_benchmark (id BIGINT PRIMARY KEY, payload TEXT NOT NULL)"
        )

    dataset = Dataset(
        ({"id": index, "payload": f"payload-{index}"} for index in range(args.rows)),
        fields=("id", "payload"),
    )
    target = PostgresTarget(target_id="postgres.benchmark", dsn=dsn, default_schema="public")
    started = time.perf_counter()
    result = target.load(
        TargetLoadRequest(
            target_id=target.target_id,
            dataset_id="benchmark.copy",
            run_id="manual-benchmark",
            dataset=dataset,
            table="pyingest_copy_benchmark",
        )
    )
    elapsed = time.perf_counter() - started
    target.close()
    engine.dispose()
    rate = result.rows_loaded / elapsed if elapsed else 0.0
    print(f"rows={result.rows_loaded} elapsed={elapsed:.3f}s rows_per_second={rate:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
