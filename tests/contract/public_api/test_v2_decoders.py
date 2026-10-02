from __future__ import annotations

import json
from pathlib import Path

from pyingestkit._api_v2 import (
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_DECODER_VALUES,
    V2_MILESTONE_CANDIDATE,
)
from pyingestkit.decoders import (
    CsvDecoder,
    DecodedType,
    Decoder,
    DecoderCapability,
    DecodeStatus,
    JsonDecoder,
    JsonDecoderConfig,
    JsonMode,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "v2_decoders.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_lot05_phase_and_milestone_are_recorded() -> None:
    payload = _fixture()

    assert "LOT-05" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-05") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_MILESTONE_CANDIDATE == payload["milestone_candidate"]
    assert "Decoder" in V2_IMPLEMENTED_DECODER_VALUES
    assert "CsvDecoder" in V2_IMPLEMENTED_DECODER_VALUES
    assert "JsonDecoder" in V2_IMPLEMENTED_DECODER_VALUES


def test_stable_decoder_ids_match_fixture() -> None:
    payload = _fixture()
    actual = [
        CsvDecoder().descriptor.id,
        JsonDecoder().descriptor.id,
        JsonDecoder(JsonDecoderConfig(mode=JsonMode.NDJSON)).descriptor.id,
    ]

    assert actual == payload["decoder_ids"]


def test_decoder_capabilities_and_statuses_match_fixture() -> None:
    payload = _fixture()

    assert [value.value for value in DecoderCapability] == payload["capabilities"]
    assert [value.value for value in DecodeStatus] == payload["decode_statuses"]
    assert [value.value for value in DecodedType] == payload["decoded_types"]


def test_decoder_protocol_surface_matches_fixture() -> None:
    payload = _fixture()

    assert all(hasattr(Decoder, name) for name in payload["protocol_methods"])
