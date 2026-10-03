"""S3-compatible DatasetVersionStore and publisher for PyIngestKit V2."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from pyingestkit.adapters.s3._objects import S3ClientV2, S3ObjectIOV2, create_s3_client_v2
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.datasets.version import DatasetVersion, dataset_content_fingerprint
from pyingestkit.domain.decoding.models import DecodedRepresentation
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank, validate_aware_datetime
from pyingestkit.serialization.dataset_version_v2 import (
    decode_dataset_snapshot,
    encode_dataset_snapshot,
)

_DATASET_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_VERSION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")


class S3DatasetVersionStoreV2:
    """Immutable S3-backed V2 version history plus one mutable current pointer."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "pyingest/v2",
        region_name: str | None = None,
        endpoint_url: str | None = None,
        client: S3ClientV2 | None = None,
    ) -> None:
        resolved_client = client or create_s3_client_v2(
            region_name=region_name,
            endpoint_url=endpoint_url,
        )
        self._objects = S3ObjectIOV2(
            bucket=bucket,
            prefix=prefix,
            client=resolved_client,
        )

    @property
    def bucket(self) -> str:
        return self._objects.bucket

    @property
    def prefix(self) -> str:
        return self._objects.prefix

    def put(self, version: DatasetVersion) -> DatasetVersionReference:
        if not isinstance(version, DatasetVersion):
            raise TypeError("S3DatasetVersionStoreV2.put expects DatasetVersion.")
        metadata_key = self._version_metadata_key(version.dataset_id, version.version_id)
        if self._objects.head(metadata_key) is not None:
            reference = self.get(version.dataset_id, version.version_id)
            self._verify(reference)
            return reference

        snapshot = encode_dataset_snapshot(version)
        snapshot_key = self._snapshot_key(version.dataset_id, version.version_id)
        self._objects.put_create_once(
            snapshot_key,
            snapshot,
            kind="dataset-snapshot",
            content_type="application/json",
        )
        locator = self._objects.uri(snapshot_key)
        payload = {
            "version_schema": "1",
            "dataset_id": version.dataset_id,
            "version_id": version.version_id,
            "created_at": (
                version.reference.created_at.isoformat()
                if version.reference.created_at is not None
                else None
            ),
            "schema_fingerprint": version.schema.fingerprint,
            "content_fingerprint": version.version_id,
            "snapshot_locator": locator,
        }
        metadata = _json_bytes(payload)
        created = self._objects.put_create_once(
            metadata_key,
            metadata,
            kind="dataset-version",
            content_type="application/json",
        )
        if not created:
            reference = self.get(version.dataset_id, version.version_id)
            self._verify(reference)
            return reference

        reference = self.get(version.dataset_id, version.version_id)
        self._verify(reference)
        return reference

    def get(self, dataset_id: str, version_id: str) -> DatasetVersionReference:
        metadata_key = self._version_metadata_key(dataset_id, version_id)
        try:
            payload = _json_object(self._objects.read(metadata_key))
        except KeyError as exc:
            raise KeyError((dataset_id, version_id)) from exc

        if payload.get("version_schema") != "1":
            raise ValueError("Unsupported S3 dataset-version metadata schema.")
        if payload.get("dataset_id") != dataset_id or payload.get("version_id") != version_id:
            raise ValueError("S3 dataset-version metadata identity mismatch.")

        snapshot_key = self._snapshot_key(dataset_id, version_id)
        locator = self._objects.uri(snapshot_key)
        if payload.get("snapshot_locator") != locator:
            raise ValueError("S3 dataset-version snapshot locator mismatch.")
        if self._objects.head(snapshot_key) is None:
            raise KeyError((dataset_id, version_id))

        created_at_raw = payload.get("created_at")
        created_at = None if created_at_raw is None else datetime.fromisoformat(str(created_at_raw))
        resource = ResourceReference(
            namespace="pyingestkit.dataset_version.s3",
            resource_id=_resource_id(locator),
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
        parts = self._dataset_parts(dataset_id)
        prefix = self._objects.key("datasets", "versions", *parts) + "/"
        values: list[DatasetVersionReference] = []
        for key in self._objects.list_keys(prefix):
            if not key.endswith("/version.json"):
                continue
            version_id = key[len(prefix) :].removesuffix("/version.json")
            if "/" in version_id or not _VERSION_ID.fullmatch(version_id):
                continue
            try:
                values.append(self.get(dataset_id, version_id))
            except (KeyError, ValueError):
                continue
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.created_at.timestamp() if item.created_at is not None else float("-inf"),
                    item.version_id,
                ),
                reverse=True,
            )
        )

    def read(self, reference: DatasetVersionReference) -> DecodedRepresentation:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError("S3DatasetVersionStoreV2.read expects DatasetVersionReference.")
        canonical = self.get(reference.dataset_id, reference.version_id)
        if reference.locator is not None and reference.locator != canonical.locator:
            raise ValueError("DatasetVersionReference locator does not match stored S3 version.")
        return self._verify(canonical)

    def publish(
        self,
        reference: DatasetVersionReference,
        *,
        ingestion_run_id: IngestionRunId,
        published_at: datetime,
    ) -> PublishedDataset:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError("S3DatasetVersionStoreV2.publish expects DatasetVersionReference.")
        if not isinstance(ingestion_run_id, IngestionRunId):
            raise TypeError("S3DatasetVersionStoreV2 ingestion_run_id must be IngestionRunId.")
        if not isinstance(published_at, datetime):
            raise TypeError("S3DatasetVersionStoreV2 published_at must be datetime.")
        validate_aware_datetime(published_at, "S3DatasetVersionStoreV2 published_at")

        stored = self.get(reference.dataset_id, reference.version_id)
        self._verify(stored)
        current = self.get_published(reference.dataset_id)
        if current is not None and current.version_id == stored.version_id:
            return current

        pointer_key = self._published_key(stored.dataset_id)
        payload = _json_bytes(
            {
                "publication_schema": "1",
                "dataset_id": stored.dataset_id,
                "version_id": stored.version_id,
                "published_at": published_at.isoformat(),
                "published_from_run_id": str(ingestion_run_id),
            }
        )
        self._objects.put_replace(
            pointer_key,
            payload,
            kind="published-dataset",
            content_type="application/json",
        )
        return PublishedDataset(
            dataset_id=stored.dataset_id,
            version=stored,
            published_at=published_at,
            published_from_run_id=ingestion_run_id,
        )

    def get_published(self, dataset_id: str) -> PublishedDataset | None:
        pointer_key = self._published_key(dataset_id)
        try:
            payload = _json_object(self._objects.read(pointer_key))
        except KeyError:
            return None
        if payload.get("publication_schema") != "1":
            raise ValueError("Unsupported S3 publication-pointer schema.")
        if payload.get("dataset_id") != dataset_id:
            raise ValueError("S3 publication-pointer dataset identity mismatch.")

        version = self.get(dataset_id, str(payload["version_id"]))
        published_at = datetime.fromisoformat(str(payload["published_at"]))
        run_id = IngestionRunId.parse(str(payload["published_from_run_id"]))
        return PublishedDataset(
            dataset_id=dataset_id,
            version=version,
            published_at=published_at,
            published_from_run_id=run_id,
        )

    def _verify(self, reference: DatasetVersionReference) -> DecodedRepresentation:
        if reference.locator is None or reference.locator.locator is None:
            raise ValueError("Stored S3 DatasetVersionReference requires a snapshot locator.")
        expected_locator = self._objects.uri(
            self._snapshot_key(reference.dataset_id, reference.version_id)
        )
        if reference.locator.locator != expected_locator:
            raise ValueError("S3 dataset-version locator disagrees with canonical storage key.")
        content = self._objects.read(
            self._snapshot_key(reference.dataset_id, reference.version_id)
        )
        schema, representation = decode_dataset_snapshot(
            content,
            expected_dataset_id=reference.dataset_id,
            expected_version_id=reference.version_id,
        )
        if schema.fingerprint != reference.schema_fingerprint:
            raise ValueError("Stored S3 dataset-version schema fingerprint mismatch.")
        if dataset_content_fingerprint(representation) != reference.version_id:
            raise ValueError("Stored S3 dataset-version content fingerprint mismatch.")
        return representation

    def _snapshot_key(self, dataset_id: str, version_id: str) -> str:
        self._validate_version_id(version_id)
        return self._objects.key(
            "datasets",
            "versions",
            *self._dataset_parts(dataset_id),
            version_id,
            "snapshot.json",
        )

    def _version_metadata_key(self, dataset_id: str, version_id: str) -> str:
        self._validate_version_id(version_id)
        return self._objects.key(
            "datasets",
            "versions",
            *self._dataset_parts(dataset_id),
            version_id,
            "version.json",
        )

    def _published_key(self, dataset_id: str) -> str:
        return self._objects.key(
            "datasets",
            "published",
            *self._dataset_parts(dataset_id),
            "current.json",
        )

    @staticmethod
    def _dataset_parts(dataset_id: str) -> tuple[str, ...]:
        require_non_blank(dataset_id, "dataset_id")
        if "/" in dataset_id or "\\" in dataset_id:
            raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
        parts = tuple(dataset_id.split("."))
        if any(not _DATASET_PART.fullmatch(part) for part in parts):
            raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
        return parts

    @staticmethod
    def _validate_version_id(version_id: str) -> None:
        if not _VERSION_ID.fullmatch(version_id):
            raise ValueError(f"Invalid dataset version id: {version_id!r}")


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_object(content: bytes) -> dict[str, object]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("S3 metadata object is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("S3 metadata object must be a JSON object.")
    return value


def _resource_id(locator: str) -> str:
    return f"dataset_version_{hashlib.sha256(locator.encode()).hexdigest()}"
