from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pyingestkit.artifacts import S3ArtifactStore
from pyingestkit.core.exceptions import SnapshotError, VersionStoreError
from pyingestkit.dataset import Dataset
from pyingestkit.metadata import MetadataStore
from pyingestkit.provenance.hashing import sha256_bytes

from ._metadata import record_published, record_version, record_version_run
from ._s3_objects import S3VersionObjectIO
from .fingerprint import DatasetFingerprint, DatasetFingerprinter
from .models import DatasetVersion, PublishedDataset
from .snapshot import SnapshotCodec
from .store import DatasetVersionStore


class S3DatasetVersionStore(DatasetVersionStore):
    """S3-backed content-addressed Dataset versions and publication pointers."""

    def __init__(
        self,
        artifact_store: S3ArtifactStore,
        *,
        metadata_store: MetadataStore | None = None,
        codec: SnapshotCodec | None = None,
    ) -> None:
        self.artifact_store = artifact_store
        self.metadata_store = metadata_store
        self.codec = codec or SnapshotCodec()
        self._objects = S3VersionObjectIO(artifact_store)

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
        self._objects.parts(dataset_id)
        fingerprint = DatasetFingerprinter().fingerprint(dataset)
        version_id = fingerprint.id
        version_key = self._objects.version_key(dataset_id, version_id)
        if self._objects.head(version_key) is not None:
            version = self.get_version(dataset_id, version_id)
            self.codec.verify(self.load_dataset(version), version_id)
            record_version(self.metadata_store, version)
            record_version_run(self.metadata_store, version, created_from_run_id)
            return version

        snapshot_payload = self.codec.encode(dataset)
        snapshot_bytes = self._objects.json_bytes(snapshot_payload)
        snapshot_key = self._objects.snapshot_key(dataset_id, version_id)
        snapshot_sha256 = sha256_bytes(snapshot_bytes)
        if self._objects.head(snapshot_key) is None:
            created = self._objects.put_create_once(
                snapshot_key,
                snapshot_bytes,
                kind="dataset-snapshot",
                sha256=snapshot_sha256,
            )
            if not created:
                snapshot_sha256 = self._verify_existing_snapshot(snapshot_key, version_id)
        else:
            snapshot_sha256 = self._verify_existing_snapshot(snapshot_key, version_id)

        version_payload: dict[str, Any] = {
            "version_schema": "1",
            "dataset_id": dataset_id,
            "version_id": version_id,
            "fingerprint": fingerprint.as_dict(),
            "snapshot_uri": self._objects.uri(snapshot_key),
            "snapshot_sha256": snapshot_sha256,
            "created_from_run_id": created_from_run_id,
            "job_id": job_id,
            "job_version": job_version,
            "source_artifact_id": source_artifact_id,
            "source_raw_sha256": source_raw_sha256,
            "quality_reports": list(quality_reports),
            "created_at": datetime.now(UTC).isoformat(),
        }
        version_bytes = self._objects.json_bytes(version_payload)
        self._objects.put_create_once(
            version_key,
            version_bytes,
            kind="dataset-version",
            sha256=sha256_bytes(version_bytes),
        )

        version = self.get_version(dataset_id, version_id)
        self.codec.verify(self.load_dataset(version), version_id)
        record_version(self.metadata_store, version)
        record_version_run(self.metadata_store, version, created_from_run_id)
        return version

    def get_version(self, dataset_id: str, version_id: str) -> DatasetVersion:
        version_key = self._objects.version_key(dataset_id, version_id)
        try:
            payload = self._objects.read_json(version_key)
        except KeyError as exc:
            raise KeyError((dataset_id, version_id)) from exc
        if payload.get("version_schema") != "1":
            raise VersionStoreError("Unsupported DatasetVersion metadata schema")
        snapshot_key = self._objects.snapshot_key(dataset_id, version_id)
        if self._objects.head(snapshot_key) is None:
            raise KeyError((dataset_id, version_id))
        if payload.get("dataset_id") != dataset_id or payload.get("version_id") != version_id:
            raise VersionStoreError("Version metadata identity does not match its S3 storage key")
        fingerprint = self._fingerprint_from(payload.get("fingerprint"))
        if fingerprint.id != version_id:
            raise VersionStoreError("Version fingerprint does not match version_id")
        snapshot_uri = self._objects.uri(snapshot_key)
        if str(payload.get("snapshot_uri")) != snapshot_uri:
            raise VersionStoreError("Version snapshot URI disagrees with its S3 storage key")
        return DatasetVersion(
            dataset_id=dataset_id,
            version_id=version_id,
            fingerprint=fingerprint,
            snapshot_uri=snapshot_uri,
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            created_from_run_id=str(payload["created_from_run_id"]),
            job_id=str(payload["job_id"]),
            job_version=str(payload["job_version"]),
            source_artifact_id=self._optional_str(payload.get("source_artifact_id")),
            source_raw_sha256=self._optional_str(payload.get("source_raw_sha256")),
            quality_reports=tuple(str(value) for value in payload.get("quality_reports", [])),
        )

    def list_versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]:
        prefix = self._objects.version_listing_prefix(dataset_id)
        versions: list[DatasetVersion] = []
        for key in self._objects.list_keys(prefix):
            if not key.endswith("/version.json"):
                continue
            version_id = key[len(prefix) :].removesuffix("/version.json")
            if "/" in version_id:
                continue
            try:
                versions.append(self.get_version(dataset_id, version_id))
            except (KeyError, VersionStoreError):
                continue
        return tuple(
            sorted(versions, key=lambda item: (item.created_at, item.version_id), reverse=True)
        )

    def load_dataset(self, version: DatasetVersion) -> Dataset:
        snapshot_key = self._objects.snapshot_key(version.dataset_id, version.version_id)
        expected_uri = self._objects.uri(snapshot_key)
        if version.snapshot_uri != expected_uri:
            raise VersionStoreError("Snapshot URI escapes or disagrees with the S3 version store")
        try:
            version_payload = self._objects.read_json(
                self._objects.version_key(version.dataset_id, version.version_id)
            )
            snapshot_bytes = self._objects.read_bytes(snapshot_key)
        except KeyError as exc:
            raise VersionStoreError(f"Snapshot object is missing: {expected_uri}") from exc
        expected_sha256 = version_payload.get("snapshot_sha256")
        if not isinstance(expected_sha256, str) or expected_sha256 != sha256_bytes(snapshot_bytes):
            raise VersionStoreError(
                f"Snapshot digest disagrees with version metadata: {expected_uri}"
            )
        try:
            payload = json.loads(snapshot_bytes)
            if not isinstance(payload, dict):
                raise SnapshotError("Snapshot root must be a JSON object")
            dataset = self.codec.decode(payload, source_artifact_id=version.source_artifact_id)
            self.codec.verify(dataset, version.version_id)
        except (UnicodeDecodeError, json.JSONDecodeError, SnapshotError) as exc:
            raise VersionStoreError(f"Invalid Dataset snapshot at {expected_uri}") from exc
        return dataset

    def get_published(self, dataset_id: str) -> PublishedDataset | None:
        key = self._objects.published_key(dataset_id)
        try:
            payload = self._objects.read_json(key)
        except KeyError:
            return None
        if payload.get("published_schema") != "1":
            raise VersionStoreError("Unsupported PublishedDataset pointer schema")
        if payload.get("dataset_id") != dataset_id:
            raise VersionStoreError("Published pointer identity mismatch")
        version = self.get_version(dataset_id, str(payload["version_id"]))
        if str(payload.get("fingerprint")) != version.fingerprint.id:
            raise VersionStoreError("Published pointer fingerprint mismatch")
        if str(payload.get("snapshot_uri")) != version.snapshot_uri:
            raise VersionStoreError("Published pointer snapshot URI mismatch")
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
        key = self._objects.published_key(version.dataset_id)
        payload = {
            "published_schema": "1",
            "dataset_id": stored.dataset_id,
            "version_id": stored.version_id,
            "fingerprint": stored.fingerprint.id,
            "snapshot_uri": stored.snapshot_uri,
            "published_at": published_at.isoformat(),
            "published_from_run_id": run_id,
        }
        data = self._objects.json_bytes(payload)
        self._objects.put_replace(
            key,
            data,
            kind="published-dataset",
            sha256=sha256_bytes(data),
        )
        published = PublishedDataset(
            dataset_id=stored.dataset_id,
            version_id=stored.version_id,
            fingerprint=stored.fingerprint,
            snapshot_uri=stored.snapshot_uri,
            published_at=published_at,
            published_from_run_id=run_id,
        )
        record_published(self.metadata_store, published)
        if self.metadata_store is not None:
            self.metadata_store.record_publication(
                run_id,
                dataset_id=stored.dataset_id,
                status="PUBLISHED",
                candidate_path=stored.snapshot_uri,
                published_path=self._objects.uri(key),
                published_at=published_at,
            )
        return published

    def _verify_existing_snapshot(self, key: str, version_id: str) -> str:
        existing = self._objects.read_bytes(key)
        try:
            payload = json.loads(existing)
            if not isinstance(payload, dict):
                raise SnapshotError("Snapshot root must be a JSON object")
            dataset = self.codec.decode(payload)
            self.codec.verify(dataset, version_id)
        except (UnicodeDecodeError, json.JSONDecodeError, SnapshotError) as exc:
            raise VersionStoreError(
                "Content-addressed snapshot key contains incompatible data"
            ) from exc
        return sha256_bytes(existing)

    @staticmethod
    def _fingerprint_from(value: object) -> DatasetFingerprint:
        if not isinstance(value, dict):
            raise VersionStoreError("Version fingerprint metadata is missing")
        try:
            return DatasetFingerprint(
                algorithm=str(value["algorithm"]),
                value=str(value["value"]),
                order_sensitive=bool(value["order_sensitive"]),
                row_count=int(value["row_count"]),
                field_count=int(value["field_count"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VersionStoreError("Invalid version fingerprint metadata") from exc

    @staticmethod
    def _optional_str(value: object) -> str | None:
        return None if value is None else str(value)
