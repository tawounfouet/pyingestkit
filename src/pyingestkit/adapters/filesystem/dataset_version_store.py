"""Filesystem LOT-08 dataset-version store and atomic publisher."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.datasets.version import DatasetVersion, dataset_content_fingerprint
from pyingestkit.domain.resources.references import ResourceReference
from pyingestkit.domain.shared.identifiers import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime
from pyingestkit.serialization.dataset_version_v2 import (
    decode_dataset_snapshot,
    encode_dataset_snapshot,
)

_DATASET_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_VERSION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")


class FileDatasetVersionStore:
    """Immutable filesystem version history plus an atomic current pointer."""

    def __init__(self, *, root: str | Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def put(self, version: DatasetVersion) -> DatasetVersionReference:
        if not isinstance(version, DatasetVersion):
            raise TypeError("FileDatasetVersionStore.put expects DatasetVersion.")
        target = self._version_dir(version.dataset_id, version.version_id)
        if target.exists():
            reference = self.get(version.dataset_id, version.version_id)
            self._verify(reference)
            return reference

        snapshot = encode_dataset_snapshot(version)
        snapshot_path = target / "snapshot.json"
        locator = snapshot_path.resolve(strict=False).as_uri()
        metadata = {
            "version_schema": "1",
            "dataset_id": version.dataset_id,
            "version_id": version.version_id,
            "created_at": version.reference.created_at.isoformat()
            if version.reference.created_at is not None
            else None,
            "schema_fingerprint": version.schema.fingerprint,
            "content_fingerprint": version.version_id,
            "snapshot_locator": locator,
        }

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / f".{version.version_id}.tmp-{uuid4().hex}"
        temporary.mkdir(mode=0o700)
        try:
            _write_bytes(temporary / "snapshot.json", snapshot)
            _write_json(temporary / "version.json", metadata)
            try:
                os.rename(temporary, target)
            except OSError:
                if not target.exists():
                    raise
                shutil.rmtree(temporary, ignore_errors=True)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        reference = self.get(version.dataset_id, version.version_id)
        self._verify(reference)
        return reference

    def get(self, dataset_id: str, version_id: str) -> DatasetVersionReference:
        target = self._version_dir(dataset_id, version_id)
        metadata_path = target / "version.json"
        snapshot_path = target / "snapshot.json"
        if not metadata_path.is_file() or not snapshot_path.is_file():
            raise KeyError((dataset_id, version_id))

        payload = _read_json(metadata_path)
        if payload.get("dataset_id") != dataset_id or payload.get("version_id") != version_id:
            raise ValueError("Dataset version metadata identity mismatch.")
        locator = snapshot_path.resolve(strict=True).as_uri()
        if payload.get("snapshot_locator") != locator:
            raise ValueError("Dataset version snapshot locator mismatch.")

        created_at_raw = payload.get("created_at")
        created_at = None if created_at_raw is None else datetime.fromisoformat(str(created_at_raw))
        resource = ResourceReference(
            namespace="pyingestkit.dataset_version.file",
            resource_id=f"dataset_version_{hashlib.sha256(locator.encode()).hexdigest()}",
            locator=locator,
            media_type="application/json",
            format="json",
        )
        return DatasetVersionReference(
            dataset_id=dataset_id,
            version_id=version_id,
            created_at=created_at,
            schema_fingerprint=str(payload["schema_fingerprint"]),
            content_fingerprint=str(payload["content_fingerprint"]),
            locator=resource,
        )

    def list(self, dataset_id: str) -> tuple[DatasetVersionReference, ...]:
        base = self._root / "versions" / Path(*self._dataset_parts(dataset_id))
        if not base.exists():
            return ()
        values: list[DatasetVersionReference] = []
        for path in base.iterdir():
            if path.is_dir() and _VERSION_ID.fullmatch(path.name):
                try:
                    values.append(self.get(dataset_id, path.name))
                except (KeyError, ValueError):
                    continue
        return tuple(
            sorted(
                values,
                key=lambda item: (item.created_at or datetime.min.astimezone(), item.version_id),
                reverse=True,
            )
        )

    def read(self, reference: DatasetVersionReference):
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError("FileDatasetVersionStore.read expects DatasetVersionReference.")
        canonical = self.get(reference.dataset_id, reference.version_id)
        if reference.locator is not None and reference.locator != canonical.locator:
            raise ValueError("DatasetVersionReference locator does not match stored version.")
        return self._verify(canonical)

    def publish(
        self,
        reference: DatasetVersionReference,
        *,
        ingestion_run_id: IngestionRunId,
        published_at: datetime,
    ) -> PublishedDataset:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError("FileDatasetVersionStore.publish expects DatasetVersionReference.")
        if not isinstance(ingestion_run_id, IngestionRunId):
            raise TypeError("FileDatasetVersionStore.publish ingestion_run_id must be IngestionRunId.")
        if not isinstance(published_at, datetime):
            raise TypeError("FileDatasetVersionStore.publish published_at must be datetime.")
        validate_aware_datetime(published_at, "FileDatasetVersionStore published_at")

        stored = self.get(reference.dataset_id, reference.version_id)
        self._verify(stored)
        current = self.get_published(reference.dataset_id)
        if current is not None and current.version_id == stored.version_id:
            return current

        pointer = self._current_path(reference.dataset_id)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "publication_schema": "1",
            "dataset_id": stored.dataset_id,
            "version_id": stored.version_id,
            "published_at": published_at.isoformat(),
            "published_from_run_id": str(ingestion_run_id),
        }
        temporary = pointer.with_name(f".{pointer.name}.tmp-{uuid4().hex}")
        _write_json(temporary, payload)
        os.replace(temporary, pointer)
        return PublishedDataset(
            dataset_id=stored.dataset_id,
            version=stored,
            published_at=published_at,
            published_from_run_id=ingestion_run_id,
        )

    def get_published(self, dataset_id: str) -> PublishedDataset | None:
        pointer = self._current_path(dataset_id)
        if not pointer.is_file():
            return None
        payload = _read_json(pointer)
        if payload.get("dataset_id") != dataset_id:
            raise ValueError("Published dataset pointer identity mismatch.")
        reference = self.get(dataset_id, str(payload["version_id"]))
        published_at = datetime.fromisoformat(str(payload["published_at"]))
        run_id = IngestionRunId.parse(str(payload["published_from_run_id"]))
        return PublishedDataset(
            dataset_id=dataset_id,
            version=reference,
            published_at=published_at,
            published_from_run_id=run_id,
        )

    def _verify(self, reference: DatasetVersionReference):
        if reference.locator is None or reference.locator.locator is None:
            raise ValueError("Stored DatasetVersionReference requires a snapshot locator.")
        snapshot_path = Path(reference.locator.locator.removeprefix("file://"))
        content = snapshot_path.read_bytes()
        schema, representation = decode_dataset_snapshot(content)
        if schema.fingerprint != reference.schema_fingerprint:
            raise ValueError("Stored dataset version schema fingerprint mismatch.")
        if dataset_content_fingerprint(representation) != reference.version_id:
            raise ValueError("Stored dataset version content fingerprint mismatch.")
        return representation

    def _version_dir(self, dataset_id: str, version_id: str) -> Path:
        if not _VERSION_ID.fullmatch(version_id):
            raise ValueError(f"Invalid dataset version id: {version_id!r}")
        return self._root / "versions" / Path(*self._dataset_parts(dataset_id)) / version_id

    def _current_path(self, dataset_id: str) -> Path:
        return self._root / "published" / Path(*self._dataset_parts(dataset_id)) / "current.json"

    @staticmethod
    def _dataset_parts(dataset_id: str) -> tuple[str, ...]:
        require_non_blank(dataset_id, "dataset_id")
        if "/" in dataset_id or "\\" in dataset_id:
            raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
        parts = tuple(dataset_id.split("."))
        if any(not _DATASET_PART.fullmatch(part) for part in parts):
            raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
        return parts


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, payload: object) -> None:
    _write_bytes(
        path,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        ),
    )


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read dataset version metadata: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Dataset version metadata must be a JSON object.")
    return payload
