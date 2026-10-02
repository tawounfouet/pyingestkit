"""Public qualified PyIngestKit V2 decoder API."""

from pyingestkit.adapters.formats import (
    CsvDecoder,
    CsvDecoderConfig,
    JsonDecoder,
    JsonDecoderConfig,
    JsonMode,
)
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.domain.decoding import (
    DecodedArray,
    DecodedObject,
    DecodedRecord,
    DecodedRepresentation,
    DecodedType,
    DecodeRequest,
    DecodeResult,
    DecoderLimits,
    DecodeStatus,
    EncodingErrorMode,
    EncodingPolicy,
    SchemaEvidence,
    SchemaFieldEvidence,
)
from pyingestkit.ports.decoders import (
    Decoder,
    DecoderCapability,
    DecoderDescriptor,
)

__all__ = [
    "CsvDecoder",
    "CsvDecoderConfig",
    "DecodeRequest",
    "DecodeResult",
    "DecodeStatus",
    "DecodedArray",
    "DecodedObject",
    "DecodedRecord",
    "DecodedRepresentation",
    "DecodedType",
    "Decoder",
    "DecoderCapability",
    "DecoderDescriptor",
    "DecoderLimits",
    "DecoderRegistry",
    "EncodingErrorMode",
    "EncodingPolicy",
    "JsonDecoder",
    "JsonDecoderConfig",
    "JsonMode",
    "SchemaEvidence",
    "SchemaFieldEvidence",
]
