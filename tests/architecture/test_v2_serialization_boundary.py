from __future__ import annotations

from pathlib import Path

from pyingestkit.serialization import BoundaryContractCodecV2, ContractEnvelopeV2

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "pickle",
    "marshal",
    "cloudpickle",
    "dill",
    "importlib",
    "pyingestkit.core",
    "pyingestkit.runtime.runner",
}


def test_lot16_serialization_is_non_executable_and_v1_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("serialization")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot16_serialization_source_contains_no_eval_or_exec() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "pyingestkit" / "serialization"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "eval(" not in source
    assert "exec(" not in source


def test_lot16_public_codec_types_are_owned_by_serialization_layer() -> None:
    assert BoundaryContractCodecV2.__module__ == "pyingestkit.serialization.contracts_v2"
    assert ContractEnvelopeV2.__module__ == "pyingestkit.serialization.envelope_v2"
