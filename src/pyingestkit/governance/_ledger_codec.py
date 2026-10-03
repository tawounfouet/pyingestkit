"""Internal portable serialization helpers for lifecycle-ledger adapters."""

from __future__ import annotations

import json
import re
from datetime import datetime

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
)
from pyingestkit.domain.runtime import CorrelationContext, FailureEvidence
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.serialization import BoundaryContractCodecV2

_SCHEMA_VERSION = 1
_SECRET_PATTERNS = (
    re.compile(r"://[^/@\s]+:[^/@\s]+@", re.IGNORECASE),
    re.compile(
        r"(?:^|[?&;\s])(?:password|passwd|pwd|secret|token|access_token|api_key|apikey)"
        r"\s*=\s*[^&;\s]+",
        re.IGNORECASE,
    ),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
)
_TERMINAL_EVENT_TYPES = frozenset(
    {
        PublicationLifecycleEventType.PUBLICATION_COMMITTED,
        PublicationLifecycleEventType.PUBLICATION_CONFLICT,
        PublicationLifecycleEventType.PUBLICATION_RECONCILED_COMMITTED,
        PublicationLifecycleEventType.PUBLICATION_RECONCILED_NOT_COMMITTED,
        PublicationLifecycleEventType.PUBLICATION_RECONCILED_CONFLICT,
        PublicationLifecycleEventType.ROLLBACK_COMMITTED,
    }
)


def encode_intent(intent: PublicationIntent) -> str:
    if not isinstance(intent, PublicationIntent):
        raise TypeError("encode_intent requires PublicationIntent.")
    codec = BoundaryContractCodecV2()
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "operation_id": str(intent.operation_id),
        "dataset_version": codec.encode(intent.dataset_version).decode("utf-8"),
        "expected_revision": str(intent.expected_revision),
        "ingestion_run_id": str(intent.ingestion_run_id),
        "correlation": codec.encode(intent.correlation).decode("utf-8"),
        "requested_at": intent.requested_at.isoformat(),
        "intent_fingerprint": intent.intent_fingerprint,
    }
    return _canonical_json(payload)


def decode_intent(content: str) -> PublicationIntent:
    payload = _parse_object(content, "publication intent")
    _exact_keys(
        payload,
        {
            "schema_version",
            "operation_id",
            "dataset_version",
            "expected_revision",
            "ingestion_run_id",
            "correlation",
            "requested_at",
            "intent_fingerprint",
        },
    )
    _require_schema(payload)

    codec = BoundaryContractCodecV2()
    dataset_version = codec.decode(_required_text(payload, "dataset_version").encode("utf-8"))
    correlation = codec.decode(_required_text(payload, "correlation").encode("utf-8"))
    if not isinstance(dataset_version, DatasetVersionReference):
        raise ValueError("Persisted publication intent dataset_version contract is invalid.")
    if not isinstance(correlation, CorrelationContext):
        raise ValueError("Persisted publication intent correlation contract is invalid.")

    intent = PublicationIntent(
        operation_id=PublicationOperationId.parse(_required_text(payload, "operation_id")),
        dataset_version=dataset_version,
        expected_revision=PublicationRevision.parse(_required_text(payload, "expected_revision")),
        ingestion_run_id=IngestionRunId.parse(_required_text(payload, "ingestion_run_id")),
        correlation=correlation,
        requested_at=_required_datetime(payload, "requested_at"),
    )
    expected_fingerprint = _required_text(payload, "intent_fingerprint")
    if intent.intent_fingerprint != expected_fingerprint:
        raise ValueError("Persisted publication intent fingerprint mismatch.")
    return intent


def encode_event(event: PublicationLifecycleEvent) -> str:
    if not isinstance(event, PublicationLifecycleEvent):
        raise TypeError("encode_event requires PublicationLifecycleEvent.")
    assert_event_persistable(event)
    codec = BoundaryContractCodecV2()
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "dataset_id": event.dataset_id,
        "occurred_at": event.occurred_at.isoformat(),
        "operation_id": None if event.operation_id is None else str(event.operation_id),
        "dataset_version": (
            None
            if event.dataset_version is None
            else codec.encode(event.dataset_version).decode("utf-8")
        ),
        "previous_revision": (
            None if event.previous_revision is None else str(event.previous_revision)
        ),
        "next_revision": None if event.next_revision is None else str(event.next_revision),
        "provider_operation_reference": event.provider_operation_reference,
        "failure": None if event.failure is None else codec.encode(event.failure).decode("utf-8"),
        "metadata": [[key, value] for key, value in event.metadata],
    }
    return _canonical_json(payload)


def decode_event(content: str) -> PublicationLifecycleEvent:
    payload = _parse_object(content, "publication lifecycle event")
    _exact_keys(
        payload,
        {
            "schema_version",
            "event_id",
            "event_type",
            "dataset_id",
            "occurred_at",
            "operation_id",
            "dataset_version",
            "previous_revision",
            "next_revision",
            "provider_operation_reference",
            "failure",
            "metadata",
        },
    )
    _require_schema(payload)
    codec = BoundaryContractCodecV2()

    dataset_raw = payload["dataset_version"]
    dataset_version = (
        None
        if dataset_raw is None
        else codec.decode(_required_text(payload, "dataset_version").encode("utf-8"))
    )
    if dataset_version is not None and not isinstance(dataset_version, DatasetVersionReference):
        raise ValueError("Persisted lifecycle event dataset_version contract is invalid.")

    failure_raw = payload["failure"]
    failure = (
        None
        if failure_raw is None
        else codec.decode(_required_text(payload, "failure").encode("utf-8"))
    )
    if failure is not None and not isinstance(failure, FailureEvidence):
        raise ValueError("Persisted lifecycle event failure contract is invalid.")

    operation_raw = payload["operation_id"]
    previous_raw = payload["previous_revision"]
    next_raw = payload["next_revision"]

    event = PublicationLifecycleEvent(
        event_id=_required_text(payload, "event_id"),
        event_type=PublicationLifecycleEventType(_required_text(payload, "event_type")),
        dataset_id=_required_text(payload, "dataset_id"),
        occurred_at=_required_datetime(payload, "occurred_at"),
        operation_id=(
            None
            if operation_raw is None
            else PublicationOperationId.parse(_required_text(payload, "operation_id"))
        ),
        dataset_version=dataset_version,
        previous_revision=(
            None
            if previous_raw is None
            else PublicationRevision.parse(_required_text(payload, "previous_revision"))
        ),
        next_revision=(
            None
            if next_raw is None
            else PublicationRevision.parse(_required_text(payload, "next_revision"))
        ),
        provider_operation_reference=_optional_text(
            payload,
            "provider_operation_reference",
        ),
        failure=failure,
        metadata=_metadata_pairs(payload["metadata"]),
    )
    assert_event_persistable(event)
    return event


def is_terminal_event(event_type: PublicationLifecycleEventType) -> bool:
    return event_type in _TERMINAL_EVENT_TYPES


def assert_event_persistable(event: PublicationLifecycleEvent) -> None:
    """Reject obvious credential/secret material before durable ledger persistence."""
    candidates: list[str] = []
    if event.provider_operation_reference is not None:
        candidates.append(event.provider_operation_reference)
    candidates.extend(value for _, value in event.metadata)
    if event.failure is not None:
        if event.failure.message_summary is not None:
            candidates.append(event.failure.message_summary)
        if event.failure.provider_code is not None:
            candidates.append(event.failure.provider_code)
        candidates.extend(value for _, value in event.failure.details)

    for value in candidates:
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise ValueError(
                "Lifecycle ledger evidence must not persist credential or secret material."
            )


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _parse_object(content: str, label: str) -> dict[str, object]:
    if not isinstance(content, str) or not content:
        raise ValueError(f"Persisted {label} must be non-empty JSON text.")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Persisted {label} is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Persisted {label} must be a JSON object.")
    return payload


def _require_schema(payload: dict[str, object]) -> None:
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("Unsupported lifecycle ledger schema version.")


def _exact_keys(payload: dict[str, object], expected: set[str]) -> None:
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"Lifecycle ledger payload fields mismatch: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}."
        )


def _required_text(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Lifecycle ledger {name} must be non-blank text.")
    return value


def _optional_text(payload: dict[str, object], name: str) -> str | None:
    value = payload.get(name)
    if value is None:
        return None
    return _required_text(payload, name)


def _required_datetime(payload: dict[str, object], name: str) -> datetime:
    value = _required_text(payload, name)
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Lifecycle ledger {name} must be ISO 8601 datetime.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"Lifecycle ledger {name} must be timezone-aware.")
    return result


def _metadata_pairs(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise ValueError("Lifecycle ledger metadata must be a JSON array.")
    pairs: list[tuple[str, str]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
        ):
            raise ValueError("Lifecycle ledger metadata entries must be [string, string].")
        pairs.append((item[0], item[1]))
    return tuple(pairs)
