from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, cast

from pyingestkit.artifacts import ArtifactURI, S3ArtifactStore
from pyingestkit.core.exceptions import VersionStoreError
from pyingestkit.logging.filters import redact_text
from pyingestkit.provenance.hashing import sha256_bytes

_DATASET_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_VERSION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")


class _S3BodyProtocol(Protocol):
    def read(self) -> bytes: ...


class _S3VersionClientProtocol(Protocol):
    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...

    def list_objects_v2(self, **kwargs: Any) -> Mapping[str, Any]: ...


class S3VersionObjectIO:
    """Internal deterministic object namespace and integrity-checked S3 I/O."""

    def __init__(self, artifact_store: S3ArtifactStore) -> None:
        self.bucket = artifact_store.bucket
        self.prefix = artifact_store.prefix
        self._client = cast(_S3VersionClientProtocol, artifact_store._client)

    def parts(self, dataset_id: str) -> tuple[str, ...]:
        if not dataset_id or "/" in dataset_id or "\\" in dataset_id:
            raise VersionStoreError(f"Invalid dataset_id: {dataset_id!r}")
        parts = tuple(dataset_id.split("."))
        if any(not _DATASET_PART.fullmatch(part) for part in parts):
            raise VersionStoreError(f"Invalid dataset_id: {dataset_id!r}")
        return parts

    def version_key(self, dataset_id: str, version_id: str) -> str:
        return f"{self.version_base_key(dataset_id, version_id)}/version.json"

    def snapshot_key(self, dataset_id: str, version_id: str) -> str:
        return f"{self.version_base_key(dataset_id, version_id)}/dataset.snapshot.json"

    def published_key(self, dataset_id: str) -> str:
        dataset_path = "/".join(self.parts(dataset_id))
        return f"{self.datasets_prefix}/published/{dataset_path}/current.json"

    def version_listing_prefix(self, dataset_id: str) -> str:
        dataset_path = "/".join(self.parts(dataset_id))
        return f"{self.datasets_prefix}/versions/{dataset_path}/"

    @property
    def datasets_prefix(self) -> str:
        return f"{self.prefix}/datasets" if self.prefix else "datasets"

    def version_base_key(self, dataset_id: str, version_id: str) -> str:
        if not _VERSION_ID.fullmatch(version_id):
            raise VersionStoreError(f"Invalid version_id: {version_id!r}")
        dataset_path = "/".join(self.parts(dataset_id))
        return f"{self.datasets_prefix}/versions/{dataset_path}/{version_id}"

    def uri(self, key: str) -> str:
        return str(ArtifactURI.s3(self.bucket, key))

    def head(self, key: str) -> Mapping[str, Any] | None:
        try:
            return self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional SDK boundary
            if self.error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                return None
            message = self.safe_error("Unable to inspect S3 version object", exc)
            raise VersionStoreError(message) from exc

    def read_bytes(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional SDK boundary
            if self.error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise KeyError(key) from exc
            message = self.safe_error("Unable to read S3 version object", exc)
            raise VersionStoreError(message) from exc
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise VersionStoreError(f"S3 response for {self.uri(key)} has no readable body")
        data = cast(_S3BodyProtocol, body).read()
        if not isinstance(data, bytes):
            raise VersionStoreError(f"S3 response for {self.uri(key)} did not return bytes")
        metadata = response.get("Metadata")
        if not isinstance(metadata, Mapping):
            raise VersionStoreError(f"S3 version object has no metadata: {self.uri(key)}")
        expected = metadata.get("pyingestkit-sha256")
        if expected is None:
            raise VersionStoreError(f"S3 version object has no SHA-256 metadata: {self.uri(key)}")
        if str(expected) != sha256_bytes(data):
            raise VersionStoreError(f"SHA-256 mismatch for S3 version object {self.uri(key)}")
        return data

    def read_json(self, key: str) -> dict[str, Any]:
        data = self.read_bytes(key)
        try:
            payload = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VersionStoreError(f"Invalid JSON version object: {self.uri(key)}") from exc
        if not isinstance(payload, dict):
            raise VersionStoreError(f"Version object must be a JSON object: {self.uri(key)}")
        return payload

    def put_create_once(self, key: str, data: bytes, *, kind: str, sha256: str) -> bool:
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/json",
                IfNoneMatch="*",
                Metadata={
                    "pyingestkit-sha256": sha256,
                    "pyingestkit-artifact-kind": kind,
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001 - optional SDK boundary
            if self.error_code(exc) in {"PreconditionFailed", "412"}:
                return False
            message = self.safe_error("Unable to persist S3 version object", exc)
            raise VersionStoreError(message) from exc

    def put_replace(self, key: str, data: bytes, *, kind: str, sha256: str) -> None:
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/json",
                Metadata={
                    "pyingestkit-sha256": sha256,
                    "pyingestkit-artifact-kind": kind,
                },
            )
        except Exception as exc:  # noqa: BLE001 - optional SDK boundary
            message = self.safe_error("Unable to publish S3 version pointer", exc)
            raise VersionStoreError(message) from exc

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        keys: list[str] = []
        continuation: str | None = None
        while True:
            request: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if continuation is not None:
                request["ContinuationToken"] = continuation
            try:
                response = self._client.list_objects_v2(**request)
            except Exception as exc:  # noqa: BLE001 - optional SDK boundary
                message = self.safe_error("Unable to list S3 versions", exc)
                raise VersionStoreError(message) from exc
            contents = response.get("Contents", [])
            if isinstance(contents, list):
                for entry in contents:
                    if isinstance(entry, Mapping) and entry.get("Key") is not None:
                        keys.append(str(entry["Key"]))
            if not bool(response.get("IsTruncated")):
                break
            token = response.get("NextContinuationToken")
            if token is None:
                raise VersionStoreError(
                    "S3 version listing was truncated without a continuation token"
                )
            continuation = str(token)
        return tuple(keys)

    @staticmethod
    def json_bytes(payload: object) -> bytes:
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def error_code(exc: BaseException) -> str | None:
        response = getattr(exc, "response", None)
        if not isinstance(response, Mapping):
            return None
        error = response.get("Error")
        if not isinstance(error, Mapping):
            return None
        code = error.get("Code")
        return None if code is None else str(code)

    def safe_error(self, prefix: str, exc: BaseException) -> str:
        return f"{prefix} bucket={self.bucket!r}: {redact_text(str(exc))}"
