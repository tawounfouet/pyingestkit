from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from pyingestkit.core.events import Event, EventType
from pyingestkit.core.exceptions import ReplayError, ReplayMismatchError
from pyingestkit.core.registry import JobRegistry
from pyingestkit.dataset import Dataset
from pyingestkit.metadata import ReplayMetadataCapability, ReplayRecord
from pyingestkit.metadata.models import ReproducibilityRecord
from pyingestkit.runtime import Runner
from pyingestkit.versioning import DatasetFingerprinter

from .models import ReplayContext, ReplayRawArtifact, ReplayResult

_REDACTED = {"***REDACTED***", "[REDACTED]"}


def _datasets(value: Any, *, _seen: set[int] | None = None) -> tuple[Dataset, ...]:
    if isinstance(value, Dataset):
        return (value,)
    seen = _seen if _seen is not None else set()
    identity = id(value)
    if identity in seen:
        return ()
    seen.add(identity)
    values: Iterable[Any]
    if isinstance(value, Mapping):
        values = value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        return ()
    result: list[Dataset] = []
    for item in values:
        result.extend(_datasets(item, _seen=seen))
    return tuple(result)


def _safe_historical_parameters(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if isinstance(item, str) and item in _REDACTED:
                continue
            result[str(key)] = _safe_historical_parameters(item)
        return result
    if isinstance(value, list):
        result_list: list[object] = []
        for item in value:
            if isinstance(item, str) and item in _REDACTED:
                continue
            result_list.append(_safe_historical_parameters(item))
        return result_list
    return value


class ReplayService:
    def __init__(self, runner: Runner, registry: JobRegistry) -> None:
        self.runner = runner
        self.registry = registry

    def replay(
        self,
        source_run_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        allow_version_change: bool = False,
        verify: bool = True,
    ) -> ReplayResult:
        try:
            source_run = self.runner.metadata_store.get_run(source_run_id)
        except (KeyError, ValueError) as exc:
            raise ReplayError(f"Source run not found or ambiguous: {source_run_id}") from exc
        try:
            job = self.registry.get(source_run.job_id)
        except KeyError as exc:
            raise ReplayError(f"Replay job is not installed: {source_run.job_id}") from exc
        if job.version != source_run.job_version and not allow_version_change:
            raise ReplayError(
                f"Installed job version {job.version} differs from source version {source_run.job_version}; use --allow-version-change to proceed"
            )

        raw_records = tuple(
            row
            for row in self.runner.metadata_store.list_artifacts(source_run.run_id)
            if row.kind == "raw"
        )
        if not raw_records:
            raise ReplayError(f"Source run has no replayable RAW artifacts: {source_run.run_id}")
        raw_artifacts = tuple(ReplayRawArtifact.from_record(row) for row in raw_records)

        expected: str | None = None
        reproducibility: ReproducibilityRecord | None = None
        metadata = self.runner.metadata_store
        if isinstance(metadata, ReplayMetadataCapability):
            expected = metadata.find_expected_fingerprint_for_run(
                source_run.run_id, source_run.job_id
            )
            reproducibility = metadata.get_run_reproducibility(source_run.run_id)

        if not verify:
            mode = "NONE"
        elif job.version != source_run.job_version:
            mode = "COMPARE"
        elif expected is None:
            mode = "BEST_EFFORT"
        else:
            mode = "STRICT"

        historical = _safe_historical_parameters(source_run.parameters)
        restored_params = dict(historical) if isinstance(historical, dict) else {}
        restored_params.update(parameters or {})
        replay_context = ReplayContext(
            source_run_id=source_run.run_id,
            source_job_id=source_run.job_id,
            source_job_version=source_run.job_version,
            raw_artifacts=raw_artifacts,
            verification_mode=mode,
            verify_expected_fingerprint=expected,
            strict=True,
        )
        run_result = self.runner.run(
            job,
            parameters=restored_params,
            fixture_mode=False,
            replay=replay_context,
            as_of=None if reproducibility is None else reproducibility.as_of,
        )

        actual: str | None = None
        if run_result.steps:
            datasets = _datasets(run_result.steps[-1].output)
            if datasets:
                actual = DatasetFingerprinter().fingerprint(datasets[0]).id
        matched: bool | None = None
        if verify and expected is not None:
            matched = actual == expected

        status = "FAILED" if not run_result.succeeded else "COMPLETED"
        if mode == "STRICT" and matched is False:
            status = "MISMATCH"

        if isinstance(metadata, ReplayMetadataCapability):
            metadata.record_replay_run(
                ReplayRecord(
                    run_id=run_result.run_id,
                    source_run_id=source_run.run_id,
                    source_job_id=source_run.job_id,
                    source_job_version=source_run.job_version,
                    executed_job_version=job.version,
                    verification_mode=mode,
                    expected_fingerprint=expected,
                    actual_fingerprint=actual,
                    status=status,
                    created_at=run_result.completed_at,
                )
            )

        verification_payload = {
            "source_run_id": source_run.run_id,
            "verification_mode": mode,
            "expected_fingerprint": expected,
            "actual_fingerprint": actual,
            "matched": matched,
        }
        self.runner._emit(
            Event(
                EventType.REPLAY_VERIFICATION_COMPLETED,
                run_result.run_id,
                job.id,
                payload=verification_payload,
            )
        )
        self._update_manifest(
            run_result.run_id, job.id, replay_context, job.version, actual, matched
        )
        self.runner._emit(
            Event(
                EventType.REPLAY_COMPLETED,
                run_result.run_id,
                job.id,
                payload={**verification_payload, "status": status},
            )
        )

        result = ReplayResult(
            run=run_result,
            source_run_id=source_run.run_id,
            source_job_version=source_run.job_version,
            executed_job_version=job.version,
            verification_mode=mode,
            expected_fingerprint=expected,
            actual_fingerprint=actual,
            matched=matched,
        )
        if mode == "STRICT" and matched is False:
            raise ReplayMismatchError(
                f"Replay Dataset fingerprint mismatch: expected {expected}, got {actual}",
                run_id=run_result.run_id,
            )
        return result

    def _update_manifest(
        self,
        run_id: str,
        job_id: str,
        replay: ReplayContext,
        executed_job_version: str,
        actual: str | None,
        matched: bool | None,
    ) -> None:
        from uuid import UUID

        run_uuid = UUID(run_id)
        path = self.runner.artifact_store.path_for(job_id, run_uuid, "manifest.json")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReplayError("Unable to update replay lineage in manifest") from exc
        lineage = replay.as_manifest_dict(executed_job_version=executed_job_version)
        lineage["actual_fingerprint"] = actual
        lineage["matched"] = matched
        payload["replay"] = lineage
        self.runner.artifact_store.write_json(job_id, run_uuid, "manifest.json", payload)
