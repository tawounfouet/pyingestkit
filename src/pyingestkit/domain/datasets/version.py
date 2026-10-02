"""Immutable V2 dataset-version semantics built from decoded evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from pyingestkit.domain.artifacts.references import ArtifactReference
from pyingestkit.domain.decoding.models import (
    DecodedArray,
    DecodedObject,
    DecodedRepresentation,
    DecodedValue,
    DecodeRequest,
    DecodeResult,
    DecodeStatus,
    SchemaEvidence,
)
from pyingestkit.domain.shared.identifiers import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime

from .references import DatasetVersionReference


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    """One immutable logical dataset version before persistence/publication."""

    reference: DatasetVersionReference
    source_artifact: ArtifactReference
    ingestion_run_id: IngestionRunId
    decoder_id: str
    schema: SchemaEvidence
    representation: DecodedRepresentation

    def __post_init__(self) -> None:
        if not isinstance(self.reference, DatasetVersionReference):
            raise TypeError("DatasetVersion reference must be DatasetVersionReference.")
        if not isinstance(self.source_artifact, ArtifactReference):
            raise TypeError("DatasetVersion source_artifact must be ArtifactReference.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("DatasetVersion ingestion_run_id must be IngestionRunId.")
        require_non_blank(self.decoder_id, "DatasetVersion decoder_id")
        if not isinstance(self.schema, SchemaEvidence):
            raise TypeError("DatasetVersion schema must be SchemaEvidence.")
        if not isinstance(self.representation, DecodedRepresentation):
            raise TypeError("DatasetVersion representation must be DecodedRepresentation.")
        if self.reference.schema_fingerprint != self.schema.fingerprint:
            raise ValueError("DatasetVersion reference schema fingerprint must match schema evidence.")
        if self.reference.content_fingerprint != self.reference.version_id:
            raise ValueError("DatasetVersion version_id must equal its content fingerprint.")

    @property
    def dataset_id(self) -> str:
        return self.reference.dataset_id

    @property
    def version_id(self) -> str:
        return self.reference.version_id

    @property
    def row_count(self) -> int:
        return len(self.representation)


def build_dataset_version(
    *,
    dataset_id: str,
    request: DecodeRequest,
    result: DecodeResult,
    created_at: datetime,
) -> DatasetVersion:
    """Promote successful decode evidence into a deterministic logical version."""

    require_non_blank(dataset_id, "DatasetVersion dataset_id")
    if not isinstance(created_at, datetime):
        raise TypeError("DatasetVersion created_at must be a datetime.")
    validate_aware_datetime(created_at, "DatasetVersion created_at")
    if result.status is not DecodeStatus.SUCCEEDED:
        raise ValueError("DatasetVersion requires a successful DecodeResult.")
    if result.representation is None or result.schema is None:
        raise ValueError("Successful DecodeResult must expose representation and schema.")
    if request.ingestion_run_id != result.ingestion_run_id:
        raise ValueError("Decode request/result ingestion_run_id mismatch.")
    if request.correlation != result.correlation:
        raise ValueError("Decode request/result correlation mismatch.")

    content_fingerprint = dataset_content_fingerprint(result.representation)
    reference = DatasetVersionReference(
        dataset_id=dataset_id,
        version_id=content_fingerprint,
        created_at=created_at,
        schema_fingerprint=result.schema.fingerprint,
        content_fingerprint=content_fingerprint,
    )
    return DatasetVersion(
        reference=reference,
        source_artifact=request.artifact,
        ingestion_run_id=result.ingestion_run_id,
        decoder_id=result.decoder_id,
        schema=result.schema,
        representation=result.representation,
    )


def dataset_content_fingerprint(representation: DecodedRepresentation) -> str:
    """Return a stable SHA-256 identity over exact decoded values and field order."""

    if not isinstance(representation, DecodedRepresentation):
        raise TypeError("dataset_content_fingerprint requires DecodedRepresentation.")
    payload = {
        "contract": "pyingestkit.dataset_content.v1",
        "records": [
            [[name, _canonical_value(value)] for name, value in record.fields]
            for record in representation.records
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256-{hashlib.sha256(encoded).hexdigest()}"


def _canonical_value(value: DecodedValue) -> object:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "number", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, DecodedObject):
        return {
            "type": "object",
            "items": [[name, _canonical_value(item)] for name, item in value.items],
        }
    if isinstance(value, DecodedArray):
        return {"type": "array", "items": [_canonical_value(item) for item in value.items]}
    raise TypeError(f"Unsupported decoded value type: {type(value).__name__}.")
