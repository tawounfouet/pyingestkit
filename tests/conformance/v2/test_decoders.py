from __future__ import annotations

from pyingestkit.decoders import (
    CsvDecoder,
    Decoder,
    DecoderCapability,
    JsonDecoder,
    JsonDecoderConfig,
    JsonMode,
)


def test_csv_decoder_satisfies_decoder_protocol() -> None:
    decoder = CsvDecoder()

    assert isinstance(decoder, Decoder)
    assert decoder.descriptor.id == "csv"
    assert DecoderCapability.SCHEMA_EVIDENCE in decoder.descriptor.capabilities
    assert DecoderCapability.ROW_COUNT in decoder.descriptor.capabilities


def test_json_decoders_have_distinct_stable_ids() -> None:
    json_decoder = JsonDecoder()
    jsonl_decoder = JsonDecoder(JsonDecoderConfig(mode=JsonMode.NDJSON))

    assert isinstance(json_decoder, Decoder)
    assert isinstance(jsonl_decoder, Decoder)
    assert json_decoder.descriptor.id == "json"
    assert jsonl_decoder.descriptor.id == "jsonl"
    assert DecoderCapability.NESTED_VALUES in json_decoder.descriptor.capabilities
