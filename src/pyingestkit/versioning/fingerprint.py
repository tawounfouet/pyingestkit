from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pyingestkit.dataset import Dataset
from pyingestkit.versioning._canonical import MISSING, canonical_value


@dataclass(frozen=True, slots=True)
class DatasetFingerprintPolicy:
    order_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class DatasetFingerprint:
    algorithm: str
    value: str
    order_sensitive: bool
    row_count: int
    field_count: int

    @property
    def id(self) -> str:
        return f"{self.algorithm}-{self.value}"

    def as_dict(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "value": self.value,
            "id": self.id,
            "order_sensitive": self.order_sensitive,
            "row_count": self.row_count,
            "field_count": self.field_count,
        }

    def __str__(self) -> str:
        return self.id


class DatasetFingerprinter:
    CODEC_VERSION = 1

    def __init__(self, policy: DatasetFingerprintPolicy | None = None) -> None:
        self.policy = policy or DatasetFingerprintPolicy()

    def fingerprint(self, dataset: Dataset) -> DatasetFingerprint:
        rows = [self._canonical_row(dataset, row) for row in dataset]
        if not self.policy.order_sensitive:
            rows.sort(key=self._dump)
        payload = {
            "codec_version": self.CODEC_VERSION,
            "kind": "dataset",
            "fields": list(dataset.fields),
            "order_sensitive": self.policy.order_sensitive,
            "rows": rows,
        }
        encoded = self._dump(payload).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return DatasetFingerprint(
            algorithm="sha256",
            value=digest,
            order_sensitive=self.policy.order_sensitive,
            row_count=dataset.row_count,
            field_count=len(dataset.fields),
        )

    @staticmethod
    def _canonical_row(dataset: Dataset, row: Mapping[str, Any]) -> object:
        return {
            "$type": "dataset-row",
            "fields": [
                [field, canonical_value(row[field] if field in row else MISSING)]
                for field in dataset.fields
            ],
        }

    @staticmethod
    def _dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
