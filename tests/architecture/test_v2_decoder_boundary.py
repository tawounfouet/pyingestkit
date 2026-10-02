from __future__ import annotations

from dataclasses import fields

from pyingestkit.domain.decoding import DecodedRepresentation, DecodeResult
from pyingestkit.ports.decoders import Decoder

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "duckdb",
    "pandas",
    "polars",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
}


def test_decoder_domain_and_port_are_engine_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("domain/decoding", "ports/decoders.py")
    ).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_decoder_protocol_does_not_own_relational_transformation() -> None:
    public = {name for name in dir(Decoder) if not name.startswith("_")}

    assert {"descriptor", "decode"}.issubset(public)
    assert public.isdisjoint(
        {
            "aggregate",
            "derive",
            "filter",
            "join",
            "pivot",
            "sort",
            "transform",
            "window",
        }
    )


def test_decode_result_exposes_framework_owned_representation() -> None:
    annotations = {field.name: str(field.type) for field in fields(DecodeResult)}

    assert "DecodedRepresentation" in annotations["representation"]
    assert DecodedRepresentation.__module__ == "pyingestkit.domain.decoding.models"
