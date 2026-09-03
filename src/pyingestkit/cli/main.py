from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyingestkit import __version__
from pyingestkit.artifacts.filesystem import LocalArtifactStore
from pyingestkit.plugins.discovery import load_registry
from pyingestkit.runtime.runner import Runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyingest", description="PyIngestKit CLI")
    parser.add_argument("--version", action="version", version=f"pyingest {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("jobs", help="List installed ingestion jobs")

    inspect_parser = sub.add_parser("inspect", help="Inspect an installed ingestion job")
    inspect_parser.add_argument("job_id")

    run_parser = sub.add_parser("run", help="Run an installed ingestion job")
    run_parser.add_argument("job_id")
    run_parser.add_argument("--workspace", default=".pyingest")
    run_parser.add_argument("--fixture", action="store_true")
    run_parser.add_argument(
        "--params-json",
        default="{}",
        help="JSON object passed as runtime parameters",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    registry = load_registry()

    if args.command == "jobs":
        for job in registry.list():
            print(f"{job.id}	{job.version}	{job.description}")
        return 0

    if args.command == "inspect":
        job = registry.get(args.job_id)
        payload = {
            "id": job.id,
            "version": job.version,
            "description": job.description,
            "depends_on": list(job.depends_on),
            "steps": [step.step_name for step in job.pipeline()],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "run":
        job = registry.get(args.job_id)
        try:
            parameters = json.loads(args.params_json)
        except json.JSONDecodeError as exc:
            parser.error(f"--params-json must be valid JSON: {exc}")
        if not isinstance(parameters, dict):
            parser.error("--params-json must decode to a JSON object")
        runner = Runner(LocalArtifactStore(Path(args.workspace)))
        result = runner.run(job, parameters=parameters, fixture_mode=args.fixture)
        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "job_id": result.job_id,
                    "status": result.status.value,
                    "duration_seconds": round(result.duration_seconds, 6),
                    "error": result.error,
                },
                indent=2,
            )
        )
        return 0 if result.succeeded else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
