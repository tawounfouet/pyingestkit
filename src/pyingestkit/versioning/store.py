from __future__ import annotations

import json
import os
import re
import shutil
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pyingestkit.core.exceptions import SnapshotError, VersionStoreError
from pyingestkit.dataset import Dataset
from pyingestkit.metadata import MetadataStore, VersionMetadataCapability
from pyingestkit.metadata.models import (
    DatasetVersionRecord,
    DatasetVersionRunRecord,
    PublishedDatasetRecord,
)

from .fingerprint import DatasetFingerprint, DatasetFingerprinter
from .models import DatasetVersion, PublishedDataset
from .snapshot import SnapshotCodec

_DATASET_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_VERSION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")


class DatasetVersionStore(ABC):
    @abstractmethod
    def create_version(
        self,
        dataset: Dataset,
        *,
        dataset_id: str,
        created_from_run_id: str,
        job_id: str,
        job_version: str,
        source_artifact_id: str | None = None,
        source_raw_sha256: str | None = None,
        quality_reports: tuple[str, ...] = (),
    ) -> DatasetVersion:
        raise NotImplementedError

    @abstractmethod
    def get_version(self, dataset_id: str, version_id: str) -> DatasetVersion:
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]:
        raise NotImplementedError

    @abstractmethod
    def load_dataset(self, version: DatasetVersion) -> Dataset:
        raise NotImplementedError

    @abstractmethod
    def get_published(self, dataset_id: str) -> PublishedDataset | None:
        raise NotImplementedError

    @abstractmethod
    def publish(self, version: DatasetVersion, *, run_id: str) -> PublishedDataset:
        raise NotImplementedError


class FilesystemDatasetVersionStore(DatasetVersionStore):
    """Content-addressed immutable Dataset versions plus an atomic current pointer."""

    def __init__(
        self,
        root: str | Path = ".pyingest",
        *,
        metadata_store: MetadataStore | None = None,
        codec: SnapshotCodec | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.metadata_store = metadata_store
        self.codec = codec or SnapshotCodec()

    def _parts(self, dataset_id: str) -> tuple[str, ...]:
        if not dataset_id or "/" in dataset_id or "\\" in dataset_id:
            raise VersionStoreError(f"Invalid dataset_id: {dataset_id!r}")
        parts = tuple(dataset_id.split("."))
        if any(not _DATASET_PART.fullmatch(part) for part in parts):
            raise VersionStoreError(f"Invalid dataset_id: {dataset_id!r}")
        return parts

    def _version_dir(self, dataset_id: str, version_id: str) -> Path:
        if not _VERSION_ID.fullmatch(version_id):
            raise VersionStoreError(f"Invalid version_id: {version_id!r}")
        return self.root / "versions" / Path(*self._parts(dataset_id)) / version_id

    def _current_path(self, dataset_id: str) -> Path:
        return self.root / "published" / Path(*self._parts(dataset_id)) / "current.json"

    def create_version(
        self,
        dataset: Dataset,
        *,
        dataset_id: str,
        created_from_run_id: str,
        job_id: str,
        job_version: str,
        source_artifact_id: str | None = None,
        source_raw_sha256: str | None = None,
        quality_reports: tuple[str, ...] = (),
    ) -> DatasetVersion:
        self._parts(dataset_id)
        fingerprint = DatasetFingerprinter().fingerprint(dataset)
        version_id = fingerprint.id
        target = self._version_dir(dataset_id, version_id)
        if target.exists():
            version = self.get_version(dataset_id, version_id)
            restored = self.load_dataset(version)
            self.codec.verify(restored, fingerprint.id)
            self._record_version(version)
            self._record_version_run(version, created_from_run_id)
            return version

        created_at = datetime.now(UTC)
        snapshot_relative = (
            Path("versions") / Path(*self._parts(dataset_id)) / version_id / "dataset.snapshot.json"
        )
        payload = self.codec.encode(dataset)
        version_payload: dict[str, Any] = {
            "version_schema": "1",
            "dataset_id": dataset_id,
            "version_id": version_id,
            "fingerprint": fingerprint.as_dict(),
            "snapshot_uri": snapshot_relative.as_posix(),
            "created_from_run_id": created_from_run_id,
            "job_id": job_id,
            "job_version": job_version,
            "source_artifact_id": source_artifact_id,
            "source_raw_sha256": source_raw_sha256,
            "quality_reports": list(quality_reports),
            "created_at": created_at.isoformat(),
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.parent / f".{version_id}.tmp-{uuid4().hex}"
        temp.mkdir(mode=0o700)
        try:
            self._write_json(temp / "dataset.snapshot.json", payload)
            self._write_json(temp / "version.json", version_payload)
            try:
                os.rename(temp, target)
            except FileExistsError:
                shutil.rmtree(temp, ignore_errors=True)
        except Exception:
            shutil.rmtree(temp, ignore_errors=True)
            raise

        version = self.get_version(dataset_id, version_id)
        restored = self.load_dataset(version)
        self.codec.verify(restored, version_id)
        self._record_version(version)
        self._record_version_run(version, created_from_run_id)
        return version

    def get_version(self, dataset_id: str, version_id: str) -> DatasetVersion:
        target = self._version_dir(dataset_id, version_id)
        metadata_path = target / "version.json"
        snapshot_path = target / "dataset.snapshot.json"
        if not metadata_path.is_file() or not snapshot_path.is_file():
            raise KeyError((dataset_id, version_id))
        payload = self._read_json(metadata_path)
        if payload.get("dataset_id") != dataset_id or payload.get("version_id") != version_id:
            raise VersionStoreError("Version metadata identity does not match its storage path")
        fingerprint_payload = payload.get("fingerprint")
        if not isinstance(fingerprint_payload, dict):
            raise VersionStoreError("Version fingerprint metadata is missing")
        fingerprint = DatasetFingerprint(
            algorithm=str(fingerprint_payload["algorithm"]),
            value=str(fingerprint_payload["value"]),
            order_sensitive=bool(fingerprint_payload["order_sensitive"]),
            row_count=int(fingerprint_payload["row_count"]),
            field_count=int(fingerprint_payload["field_count"]),
        )
        if fingerprint.id != version_id:
            raise VersionStoreError("Version fingerprint does not match version_id")
        return DatasetVersion(
            dataset_id=dataset_id,
            version_id=version_id,
            fingerprint=fingerprint,
            snapshot_uri=str(payload["snapshot_uri"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            created_from_run_id=str(payload["created_from_run_id"]),
            job_id=str(payload["job_id"]),
            job_version=str(payload["job_version"]),
            source_artifact_id=self._optional_str(payload.get("source_artifact_id")),
            source_raw_sha256=self._optional_str(payload.get("source_raw_sha256")),
            quality_reports=tuple(str(v) for v in payload.get("quality_reports", [])),
        )

    def list_versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]:
        base = self.root / "versions" / Path(*self._parts(dataset_id))
        if not base.exists():
            return ()
        versions: list[DatasetVersion] = []
        for path in base.iterdir():
            if path.is_dir() and _VERSION_ID.fullmatch(path.name):
                try:
                    versions.append(self.get_version(dataset_id, path.name))
                except (KeyError, VersionStoreError):
                    continue
        return tuple(sorted(versions, key=lambda item: (item.created_at, item.version_id), reverse=True))

    def load_dataset(self, version: DatasetVersion) -> Dataset:
        expected = self._version_dir(version.dataset_id, version.version_id) / "dataset.snapshot.json"
        uri_path = (self.root / version.snapshot_uri).resolve()
        if uri_path != expected.resolve() or self.root not in uri_path.parents:
            raise VersionStoreError("Snapshot URI escapes or disagrees with the version store")
        payload = self._read_json(uri_path)
        try:
            dataset = self.codec.decode(payload, source_artifact_id=version.source_artifact_id)
            self.codec.verify(dataset, version.version_id)
        except SnapshotError:
            raise
        return dataset

    def get_published(self, dataset_id: str) -> PublishedDataset | None:
        current = self._current_path(dataset_id)
        if not current.is_file():
            return None
        payload = self._read_json(current)
        if payload.get("dataset_id") != dataset_id:
            raise VersionStoreError("Published pointer identity mismatch")
        version = self.get_version(dataset_id, str(payload["version_id"]))
        return PublishedDataset(
            dataset_id=dataset_id,
            version_id=version.version_id,
            fingerprint=version.fingerprint,
            snapshot_uri=version.snapshot_uri,
            published_at=datetime.fromisoformat(str(payload["published_at"])),
            published_from_run_id=str(payload["published_from_run_id"]),
        )

    def publish(self, version: DatasetVersion, *, run_id: str) -> PublishedDataset:
        stored = self.get_version(version.dataset_id, version.version_id)
        current = self.get_published(version.dataset_id)
        if current is not None and current.version_id == stored.version_id:
            return current
        published_at = datetime.now(UTC)
        pointer = self._current_path(version.dataset_id)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "published_schema": "1",
            "dataset_id": version.dataset_id,
            "version_id": version.version_id,
            "fingerprint": version.fingerprint.id,
            "snapshot_uri": version.snapshot_uri,
            "published_at": published_at.isoformat(),
            "published_from_run_id": run_id,
        }
        temp = pointer.with_name(f".{pointer.name}.tmp-{uuid4().hex}")
        self._write_json(temp, payload)
        os.replace(temp, pointer)
        published = PublishedDataset(
            dataset_id=version.dataset_id,
            version_id=version.version_id,
            fingerprint=version.fingerprint,
            snapshot_uri=version.snapshot_uri,
            published_at=published_at,
            published_from_run_id=run_id,
        )
        self._record_published(published)
        if self.metadata_store is not None:
            self.metadata_store.record_publication(
                run_id,
                dataset_id=version.dataset_id,
                status="PUBLISHED",
                candidate_path=version.snapshot_uri,
                published_path=str(pointer),
                published_at=published_at,
            )
        return published

    def _record_version(self, version: DatasetVersion) -> None:
        if isinstance(self.metadata_store, VersionMetadataCapability):
            self.metadata_store.record_dataset_version(
                DatasetVersionRecord(
                    dataset_id=version.dataset_id,
                    version_id=version.version_id,
                    fingerprint=version.fingerprint.id,
                    snapshot_uri=version.snapshot_uri,
                    created_from_run_id=version.created_from_run_id,
                    job_id=version.job_id,
                    job_version=version.job_version,
                    source_artifact_id=version.source_artifact_id,
                    source_raw_sha256=version.source_raw_sha256,
                    created_at=version.created_at,
                )
            )

    def _record_version_run(self, version: DatasetVersion, run_id: str) -> None:
        if isinstance(self.metadata_store, VersionMetadataCapability):
            self.metadata_store.record_dataset_version_run(
                DatasetVersionRunRecord(
                    dataset_id=version.dataset_id,
                    version_id=version.version_id,
                    run_id=run_id,
                    created_at=datetime.now(UTC),
                )
            )

    def _record_published(self, published: PublishedDataset) -> None:
        if isinstance(self.metadata_store, VersionMetadataCapability):
            self.metadata_store.record_published_dataset(
                PublishedDatasetRecord(
                    dataset_id=published.dataset_id,
                    version_id=published.version_id,
                    published_from_run_id=published.published_from_run_id,
                    published_at=published.published_at,
                )
            )

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VersionStoreError(f"Unable to read version data: {path}") from exc
        if not isinstance(payload, dict):
            raise VersionStoreError(f"Version data must be a JSON object: {path}")
        return payload

    @staticmethod
    def _optional_str(value: object) -> str | None:
        return None if value is None else str(value)
