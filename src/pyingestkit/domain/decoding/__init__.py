"""PyIngestKit V2 decode-domain contracts."""

from pyingestkit.domain.decoding.models import (
    DecodeRequest,
    DecodeResult,
    DecodeStatus,
    DecodedArray,
    DecodedObject,
    DecodedRecord,
    DecodedRepresentation,
    DecodedScalar,
    DecodedType,
    DecodedValue,
    SchemaEvidence,
    SchemaFieldEvidence,
)
from pyingestkit.domain.decoding.policy import (
    DecoderLimits,
    EncodingErrorMode,
    EncodingPolicy,
)

__all__ = [
    "DecodeRequest",
    "DecodeResult",
    "DecodeStatus",
    "DecodedArray",
    "DecodedObject",
    "DecodedRecord",
    "DecodedRepresentation",
    "DecodedScalar",
    "DecodedType",
    "DecodedValue",
    "DecoderLimits",
    "EncodingErrorMode",
    "EncodingPolicy",
    "SchemaEvidence",
    "SchemaFieldEvidence",
]
