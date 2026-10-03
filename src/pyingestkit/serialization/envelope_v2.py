"""Canonical, non-executable wire envelopes for PyIngestKit V2 contracts."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
MigrationV2: TypeAlias = Callable[[dict[str, JsonValue]], dict[str, JsonValue]]


@dataclass(frozen=True, slots=True)
class ContractEnvelopeV2:
    """Validated wire envelope carrying one versioned contract payload."""

    contract_id: str
    contract_version: str
    payload: dict[str, JsonValue]
    envelope_version: str = "1"

    def __post_init__(self) -> None:
        for name, value in (
            ("contract_id", self.contract_id),
            ("contract_version", self.contract_version),
            ("envelope_version", self.envelope_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ContractEnvelopeV2 {name} must be non-blank text.")
        if self.envelope_version != "1":
            raise ValueError("Unsupported ContractEnvelopeV2 envelope_version.")
        if not isinstance(self.payload, dict):
            raise TypeError("ContractEnvelopeV2 payload must be a dict.")
        _validate_json_value(self.payload)

    def canonical_bytes(self) -> bytes:
        """Return deterministic UTF-8 JSON with no insignificant whitespace."""
        return json.dumps(
            {
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "envelope_version": self.envelope_version,
                "payload": self.payload,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @classmethod
    def parse(cls, content: bytes) -> ContractEnvelopeV2:
        """Parse and validate one canonical envelope without importing code from it."""
        if not isinstance(content, bytes):
            raise TypeError("ContractEnvelopeV2.parse content must be bytes.")
        try:
            decoded = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Contract envelope is not valid UTF-8 JSON.") from exc
        if not isinstance(decoded, dict):
            raise ValueError("Contract envelope root must be a JSON object.")
        expected = {"contract_id", "contract_version", "envelope_version", "payload"}
        if set(decoded) != expected:
            raise ValueError("Contract envelope fields do not match the V2 envelope schema.")
        payload = decoded["payload"]
        if not isinstance(payload, dict):
            raise ValueError("Contract envelope payload must be a JSON object.")
        return cls(
            contract_id=_text(decoded["contract_id"], "contract_id"),
            contract_version=_text(decoded["contract_version"], "contract_version"),
            envelope_version=_text(decoded["envelope_version"], "envelope_version"),
            payload=payload,
        )


class ContractMigrationRegistryV2:
    """Explicit adjacent-version payload migrations; no dynamic code loading."""

    def __init__(self) -> None:
        self._steps: dict[tuple[str, str], tuple[str, MigrationV2]] = {}

    def register(
        self,
        *,
        contract_id: str,
        from_version: str,
        to_version: str,
        migrate: MigrationV2,
    ) -> None:
        for name, value in (
            ("contract_id", contract_id),
            ("from_version", from_version),
            ("to_version", to_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Migration {name} must be non-blank text.")
        if from_version == to_version:
            raise ValueError("Migration versions must differ.")
        if not callable(migrate):
            raise TypeError("Migration function must be callable.")
        key = (contract_id, from_version)
        if key in self._steps:
            raise ValueError("Migration step is already registered.")
        self._steps[key] = (to_version, migrate)

    def migrate(
        self,
        envelope: ContractEnvelopeV2,
        *,
        target_version: str,
    ) -> ContractEnvelopeV2:
        if not isinstance(envelope, ContractEnvelopeV2):
            raise TypeError("migrate expects ContractEnvelopeV2.")
        if not isinstance(target_version, str) or not target_version.strip():
            raise ValueError("target_version must be non-blank text.")
        current = envelope
        visited: set[str] = set()
        while current.contract_version != target_version:
            if current.contract_version in visited:
                raise ValueError("Contract migration graph contains a cycle.")
            visited.add(current.contract_version)
            step = self._steps.get((current.contract_id, current.contract_version))
            if step is None:
                raise ValueError(
                    "No registered migration path for "
                    f"{current.contract_id} version {current.contract_version!r}."
                )
            next_version, migrate = step
            migrated = migrate(dict(current.payload))
            if not isinstance(migrated, dict):
                raise TypeError("Contract migration must return a dict payload.")
            current = ContractEnvelopeV2(
                contract_id=current.contract_id,
                contract_version=next_version,
                payload=migrated,
            )
        return current


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("Contract payload must not contain NaN or infinity.")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Contract payload object keys must be strings.")
            _validate_json_value(item)
        return
    raise TypeError(f"Unsupported contract payload type: {type(value).__name__}.")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Contract envelope {name} must be non-blank text.")
    return value
