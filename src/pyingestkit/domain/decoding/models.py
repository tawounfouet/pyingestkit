"""Immutable decode contracts and dependency-neutral representation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from pyingestkit.domain.artifacts.references import ArtifactReference
from pyingestkit.domain.runtime.context import CorrelationContext
from pyingestkit.domain.runtime.diagnostics import Diagnostic
from pyingestkit.domain.runtime.failure import FailureEvidence
from pyingestkit.domain.shared.identifiers import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank


class DecodeStatus(StrEnum):
    """Outcome of one decode operation."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return True


class DecodedType(StrEnum):
    """Portable value categories observed during decoding."""

    NULL = "null"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    OBJECT = "object"
    ARRAY = "array"


DecodedScalar: TypeAlias = None | bool | int | float | str


@dataclass(frozen=True, slots=True)
class DecodedObject:
    """Immutable decoded object preserving field order."""

    items: tuple[tuple[str, DecodedValue], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            raise TypeError("DecodedObject items must be a tuple.")
        names: set[str] = set()
        for item in self.items:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("DecodedObject items must contain key/value pairs.")
            name, _ = item
            require_non_blank(name, "DecodedObject field name")
            if name in names:
                raise ValueError(f"DecodedObject contains duplicate field {name!r}.")
            names.add(name)


@dataclass(frozen=True, slots=True)
class DecodedArray:
    """Immutable decoded array preserving element order."""

    items: tuple[DecodedValue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            raise TypeError("DecodedArray items must be a tuple.")


DecodedValue: TypeAlias = DecodedScalar | DecodedObject | DecodedArray


@dataclass(frozen=True, slots=True)
class DecodedRecord:
    """One immutable record in a dependency-neutral decoded representation."""

    fields: tuple[tuple[str, DecodedValue], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.fields, tuple):
            raise TypeError("DecodedRecord fields must be a tuple.")
        names: set[str] = set()
        for item in self.fields:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("DecodedRecord fields must contain key/value pairs.")
            name, _ = item
            require_non_blank(name, "DecodedRecord field name")
            if name in names:
                raise ValueError(f"DecodedRecord contains duplicate field {name!r}.")
            names.add(name)

    def get(self, name: str) -> DecodedValue:
        """Return one field value by name."""
        require_non_blank(name, "DecodedRecord field lookup")
        for field_name, value in self.fields:
            if field_name == name:
                return value
        raise KeyError(name)


@dataclass(frozen=True, slots=True)
class DecodedRepresentation:
    """Framework-owned immutable record representation."""

    records: tuple[DecodedRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise TypeError("DecodedRepresentation records must be a tuple.")
        if any(not isinstance(record, DecodedRecord) for record in self.records):
            raise TypeError("DecodedRepresentation records must contain DecodedRecord values.")

    def __len__(self) -> int:
        return len(self.records)


@dataclass(frozen=True, slots=True)
class SchemaFieldEvidence:
    """Observed type/nullability evidence for one decoded field."""

    name: str
    observed_types: tuple[DecodedType, ...]
    nullable: bool

    def __post_init__(self) -> None:
        require_non_blank(self.name, "SchemaFieldEvidence name")
        if not isinstance(self.observed_types, tuple):
            raise TypeError("SchemaFieldEvidence observed_types must be a tuple.")
        if not self.observed_types:
            raise ValueError("SchemaFieldEvidence requires at least one observed type.")
        if any(not isinstance(value, DecodedType) for value in self.observed_types):
            raise TypeError("SchemaFieldEvidence observed_types must contain DecodedType values.")
        if len(set(self.observed_types)) != len(self.observed_types):
            raise ValueError("SchemaFieldEvidence observed_types must be unique.")
        if not isinstance(self.nullable, bool):
            raise TypeError("SchemaFieldEvidence nullable must be bool.")


@dataclass(frozen=True, slots=True)
class SchemaEvidence:
    """Deterministic observed schema evidence for decoded records."""

    fields: tuple[SchemaFieldEvidence, ...]
    fingerprint_algorithm: str = "sha256"
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.fields, tuple):
            raise TypeError("SchemaEvidence fields must be a tuple.")
        if any(not isinstance(field, SchemaFieldEvidence) for field in self.fields):
            raise TypeError("SchemaEvidence fields must contain SchemaFieldEvidence values.")
        names = tuple(field.name for field in self.fields)
        if len(set(names)) != len(names):
            raise ValueError("SchemaEvidence field names must be unique.")
        if self.fingerprint_algorithm != "sha256":
            raise ValueError("SchemaEvidence fingerprint_algorithm must be 'sha256'.")

        expected = schema_fingerprint(self.fields)
        if self.fingerprint:
            if self.fingerprint != expected:
                raise ValueError("SchemaEvidence fingerprint does not match field evidence.")
        else:
            object.__setattr__(self, "fingerprint", expected)


@dataclass(frozen=True, slots=True)
class DecodeRequest:
    """One explicit request to decode exact durable RAW bytes."""

    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    artifact: ArtifactReference
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("DecodeRequest ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("DecodeRequest correlation must be a CorrelationContext.")
        if not isinstance(self.artifact, ArtifactReference):
            raise TypeError("DecodeRequest artifact must be an ArtifactReference.")
        if self.artifact.kind != "raw":
            raise ValueError("DecodeRequest artifact must reference RAW evidence.")
        if not isinstance(self.content, bytes):
            raise TypeError("DecodeRequest content must be bytes.")
        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "DecodeRequest correlation ingestion_run_id must match the native IngestionRunId."
            )


@dataclass(frozen=True, slots=True)
class DecodeResult:
    """Structured decode evidence plus dependency-neutral runtime representation."""

    status: DecodeStatus
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    decoder_id: str
    decoder_version: str
    representation: DecodedRepresentation | None = None
    schema: SchemaEvidence | None = None
    row_count: int | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    rejected_artifact: ArtifactReference | None = None
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, DecodeStatus):
            raise TypeError("DecodeResult status must be DecodeStatus.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("DecodeResult ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("DecodeResult correlation must be a CorrelationContext.")
        require_non_blank(self.decoder_id, "DecodeResult decoder_id")
        require_non_blank(self.decoder_version, "DecodeResult decoder_version")

        if self.representation is not None and not isinstance(
            self.representation,
            DecodedRepresentation,
        ):
            raise TypeError("DecodeResult representation must be DecodedRepresentation.")
        if self.schema is not None and not isinstance(self.schema, SchemaEvidence):
            raise TypeError("DecodeResult schema must be SchemaEvidence.")
        if self.row_count is not None:
            if not isinstance(self.row_count, int):
                raise TypeError("DecodeResult row_count must be int.")
            if self.row_count < 0:
                raise ValueError("DecodeResult row_count must be non-negative.")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("DecodeResult diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError("DecodeResult diagnostics must contain Diagnostic values.")
        if self.rejected_artifact is not None and not isinstance(
            self.rejected_artifact,
            ArtifactReference,
        ):
            raise TypeError("DecodeResult rejected_artifact must be ArtifactReference.")
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("DecodeResult failure must be FailureEvidence.")

        if self.status is DecodeStatus.SUCCEEDED:
            if self.representation is None or self.schema is None or self.row_count is None:
                raise ValueError(
                    "Successful DecodeResult requires representation, schema and row_count."
                )
            if self.row_count != len(self.representation):
                raise ValueError("DecodeResult row_count must equal representation length.")
            if self.failure is not None:
                raise ValueError("Successful DecodeResult cannot contain FailureEvidence.")
        else:
            if self.failure is None:
                raise ValueError("Failed DecodeResult requires FailureEvidence.")
            if self.representation is not None or self.schema is not None:
                raise ValueError("Failed DecodeResult cannot expose decoded representation/schema.")
            if self.row_count is not None:
                raise ValueError("Failed DecodeResult cannot claim row_count.")


def schema_fingerprint(fields: tuple[SchemaFieldEvidence, ...]) -> str:
    """Return deterministic SHA-256 over portable schema evidence."""
    payload = [
        {
            "name": field.name,
            "observed_types": [value.value for value in field.observed_types],
            "nullable": field.nullable,
        }
        for field in fields
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
