"""PyIngestKit V2 decode-domain contracts."""

from pyingestkit.domain.decoding.models import (
    DecodedArray,
    DecodedObject,
    DecodedRecord,
    DecodedRepresentation,
    DecodedScalar,
    DecodedType,
    DecodedValue,
    DecodeRequest,
    DecodeResult,
    DecodeStatus,
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
