from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pyingestkit.core.exceptions import ConfigurationError, StorageError
from pyingestkit.logging.filters import redact_text
from pyingestkit.provenance.hashing import sha256_bytes

from .base import ArtifactStore
from .filesystem import LocalArtifactStore
from .naming import run_relative_key, safe_component
from .raw import RawArtifact
from .uri import ArtifactURI

logger = logging.getLogger(__name__)


class S3BodyProtocol(Protocol):
    def read(self) -> bytes: ...


class S3ClientProtocol(Protocol):
    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...


class S3ArtifactStore(ArtifactStore):
    """Immutable remote RAW storage with a local parser-facing materialization cache."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "pyingest",
        cache_root: str | Path = ".pyingest",
        region_name: str | None = None,
        endpoint_url: str | None = None,
        client: S3ClientProtocol | None = None,
    ) -> None:
        normalized_bucket = bucket.strip()
        if not normalized_bucket or any(char.isspace() for char in normalized_bucket):
            raise ConfigurationError("S3ArtifactStore requires a non-empty bucket")
        if any(char in normalized_bucket for char in ("/", "@", ":")):
            raise ConfigurationError("S3ArtifactStore bucket contains invalid characters")
        normalized_prefix = prefix.strip("/")
        if ".." in normalized_prefix.split("/"):
            raise ConfigurationError("S3ArtifactStore prefix must not contain '..'")
        if endpoint_url is not None:
            parsed = urlsplit(endpoint_url)
            if parsed.username is not None or parsed.password is not None:
                raise ConfigurationError("S3 endpoint URL must not embed credentials")
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ConfigurationError("S3 endpoint URL must be an absolute HTTP(S) URL")

        self.bucket = normalized_bucket
        self.prefix = normalized_prefix
        self.cache_root = Path(cache_root)
        # Compatibility surface used by local DatasetVersion reference jobs.
        self.root = self.cache_root
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self._local = LocalArtifactStore(self.cache_root)
        self._client = client or self._create_client(
            region_name=region_name,
            endpoint_url=endpoint_url,
        )

    @staticmethod
    def _create_client(*, region_name: str | None, endpoint_url: str | None) -> S3ClientProtocol:
        try:
            import boto3  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise ConfigurationError(
                "S3ArtifactStore requires boto3. Install PyIngestKit with the 's3' extra."
            ) from exc
        return cast(
            S3ClientProtocol,
            boto3.client("s3", region_name=region_name, endpoint_url=endpoint_url),
        )

    def prepare_run(self, job_id: str, run_id: UUID) -> Path:
        return self._local.prepare_run(job_id, run_id)

    def path_for(self, job_id: str, run_id: UUID, relative_path: str) -> Path:
        return self._local.path_for(job_id, run_id, relative_path)

    def write_json(self, job_id: str, run_id: UUID, relative_path: str, payload: Any) -> Path:
        # A2 intentionally keeps manifests/reports local. Only immutable RAW is remote.
        return self._local.write_json(job_id, run_id, relative_path, payload)

    def _key_for(self, job_id: str, run_id: UUID, relative_path: str) -> str:
        relative = run_relative_key(job_id, run_id, relative_path)
        return f"{self.prefix}/{relative}" if self.prefix else relative

    def uri_for(self, job_id: str, run_id: UUID, relative_path: str) -> ArtifactURI:
        return ArtifactURI.s3(self.bucket, self._key_for(job_id, run_id, relative_path))

    def _head(self, key: str) -> Mapping[str, Any] | None:
        try:
            return self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional SDK defines backend exceptions
            if self._error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise StorageError(self._safe_error("Unable to inspect S3 RAW object", exc)) from exc

    @staticmethod
    def _error_code(exc: BaseException) -> str | None:
        response = getattr(exc, "response", None)
        if not isinstance(response, Mapping):
            return None
        error = response.get("Error")
        if not isinstance(error, Mapping):
            return None
        code = error.get("Code")
        return None if code is None else str(code)

    def _safe_error(self, prefix: str, exc: BaseException) -> str:
        message = redact_text(str(exc))
        return f"{prefix} bucket={self.bucket!r}: {message}"

    def write_raw(
        self,
        job_id: str,
        run_id: UUID,
        *,
        name: str,
        data: bytes,
        source_uri: str,
        content_type: str | None = None,
        resolved_url: str | None = None,
        status_code: int | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> RawArtifact:
        self.prepare_run(job_id, run_id)
        relative_path = f"raw/{safe_component(name)}"
        key = self._key_for(job_id, run_id, relative_path)
        if self._head(key) is not None:
            raise StorageError(
                f"RAW artifacts are immutable: refusing to overwrite s3://{self.bucket}/{key}"
            )

        digest = sha256_bytes(data)
        artifact_id = str(uuid4())
        local_path = self.path_for(job_id, run_id, relative_path)
        try:
            with local_path.open("xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise StorageError(
                f"RAW artifacts are immutable: refusing to overwrite existing cache path {local_path}"
            ) from exc

        request: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "IfNoneMatch": "*",
            "Metadata": {
                "pyingestkit-sha256": digest,
                "pyingestkit-artifact-id": artifact_id,
            },
        }
        if content_type is not None:
            request["ContentType"] = content_type
        try:
            self._client.put_object(**request)
        except Exception as exc:  # noqa: BLE001 - optional SDK defines backend exceptions
            local_path.unlink(missing_ok=True)
            if self._error_code(exc) in {"PreconditionFailed", "412"}:
                raise StorageError(
                    f"RAW artifacts are immutable: concurrent object already exists s3://{self.bucket}/{key}"
                ) from exc
            raise StorageError(self._safe_error("Unable to persist S3 RAW object", exc)) from exc

        logger.debug(
            "S3 RAW artifact written uri=s3://%s/%s bytes=%d sha256=%s",
            self.bucket,
            key,
            len(data),
            digest,
        )
        return RawArtifact(
            artifact_id=artifact_id,
            source_uri=source_uri,
            retrieved_at=datetime.now(UTC),
            content_type=content_type,
            size_bytes=len(data),
            sha256=digest,
            path=str(local_path),
            storage_uri=str(ArtifactURI.s3(self.bucket, key)),
            resolved_url=resolved_url,
            status_code=status_code,
            etag=etag,
            last_modified=last_modified,
        )

    def read_bytes(self, uri: ArtifactURI | str) -> bytes:
        location = uri if isinstance(uri, ArtifactURI) else ArtifactURI(uri)
        if location.scheme != "s3":
            return super().read_bytes(location)
        if location.bucket != self.bucket:
            raise StorageError(
                f"S3ArtifactStore for bucket {self.bucket!r} refuses URI for bucket {location.bucket!r}"
            )
        key = location.key
        if key is None:
            raise StorageError(f"Invalid S3 artifact URI: {location}")
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            body = response.get("Body")
            if body is None or not hasattr(body, "read"):
                raise StorageError(f"S3 response for {location} does not contain a readable body")
            data = cast(S3BodyProtocol, body).read()
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001 - optional SDK defines backend exceptions
            raise StorageError(self._safe_error("Unable to read S3 RAW object", exc)) from exc
        if not isinstance(data, bytes):
            raise StorageError(f"S3 response for {location} did not return bytes")
        return data
