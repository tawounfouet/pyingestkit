"""Minimal S3-compatible object I/O shared by PyIngestKit V2 stores."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Protocol, cast
from urllib.parse import urlsplit


class S3BodyV2(Protocol):
    def read(self) -> bytes: ...


class S3ClientV2(Protocol):
    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...

    def list_objects_v2(self, **kwargs: Any) -> Mapping[str, Any]: ...


def create_s3_client_v2(
    *,
    region_name: str | None,
    endpoint_url: str | None,
) -> S3ClientV2:
    """Create the optional boto3 client only when a caller actually needs it."""
    if endpoint_url is not None:
        parsed = urlsplit(endpoint_url)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("S3 endpoint URL must not embed credentials.")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("S3 endpoint URL must be absolute HTTP(S).")
    try:
        import boto3  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "S3 V2 adapters require boto3. Install PyIngestKit with the 's3' extra."
        ) from exc
    return cast(
        S3ClientV2,
        boto3.client("s3", region_name=region_name, endpoint_url=endpoint_url),
    )


class S3ObjectIOV2:
    """Integrity-aware object I/O over one bucket/prefix."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        client: S3ClientV2,
    ) -> None:
        normalized_bucket = bucket.strip()
        if not normalized_bucket or any(char.isspace() for char in normalized_bucket):
            raise ValueError("S3 bucket must be non-blank and contain no whitespace.")
        if any(char in normalized_bucket for char in ("/", "@", ":")):
            raise ValueError("S3 bucket contains invalid characters.")
        normalized_prefix = prefix.strip("/")
        if any(part in {"", ".", ".."} for part in normalized_prefix.split("/") if normalized_prefix):
            raise ValueError("S3 prefix contains an unsafe path component.")
        self.bucket = normalized_bucket
        self.prefix = normalized_prefix
        self.client = client

    def key(self, *parts: str) -> str:
        safe: list[str] = []
        for part in parts:
            if not isinstance(part, str) or not part or part in {".", ".."}:
                raise ValueError("S3 object-key components must be non-blank safe text.")
            if "/" in part or "\\" in part or "\x00" in part:
                raise ValueError("S3 object-key components must not contain path separators.")
            safe.append(part)
        relative = "/".join(safe)
        return f"{self.prefix}/{relative}" if self.prefix else relative

    def uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    def head(self, key: str) -> Mapping[str, Any] | None:
        try:
            return self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            if _error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise RuntimeError("Unable to inspect S3 object.") from exc

    def put_create_once(
        self,
        key: str,
        content: bytes,
        *,
        kind: str,
        content_type: str | None = None,
    ) -> bool:
        if self.head(key) is not None:
            return False
        digest = hashlib.sha256(content).hexdigest()
        request: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": content,
            "IfNoneMatch": "*",
            "Metadata": {
                "pyingestkit-sha256": digest,
                "pyingestkit-kind": kind,
            },
        }
        if content_type is not None:
            request["ContentType"] = content_type
        try:
            self.client.put_object(**request)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            if _error_code(exc) in {"412", "PreconditionFailed"}:
                return False
            raise RuntimeError("Unable to create immutable S3 object.") from exc
        return True

    def put_replace(
        self,
        key: str,
        content: bytes,
        *,
        kind: str,
        content_type: str | None = None,
    ) -> None:
        digest = hashlib.sha256(content).hexdigest()
        request: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": content,
            "Metadata": {
                "pyingestkit-sha256": digest,
                "pyingestkit-kind": kind,
            },
        }
        if content_type is not None:
            request["ContentType"] = content_type
        try:
            self.client.put_object(**request)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            raise RuntimeError("Unable to replace S3 object.") from exc

    def read(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            if _error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise KeyError(key) from exc
            raise RuntimeError("Unable to read S3 object.") from exc
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise RuntimeError("S3 object response does not contain a readable body.")
        content = cast(S3BodyV2, body).read()
        if not isinstance(content, bytes):
            raise RuntimeError("S3 object body did not return bytes.")

        metadata = response.get("Metadata")
        if not isinstance(metadata, Mapping):
            raise RuntimeError("S3 object is missing integrity metadata.")
        expected = metadata.get("pyingestkit-sha256")
        actual = hashlib.sha256(content).hexdigest()
        if expected != actual:
            raise ValueError("S3 object SHA-256 metadata does not match stored bytes.")
        return content

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        values: list[str] = []
        token: str | None = None
        while True:
            request: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": prefix,
            }
            if token is not None:
                request["ContinuationToken"] = token
            try:
                response = self.client.list_objects_v2(**request)
            except Exception as exc:  # noqa: BLE001 - optional provider boundary
                raise RuntimeError("Unable to list S3 objects.") from exc
            contents = response.get("Contents", ())
            if contents is None:
                contents = ()
            for item in contents:
                if isinstance(item, Mapping) and isinstance(item.get("Key"), str):
                    values.append(str(item["Key"]))
            if not response.get("IsTruncated"):
                break
            next_token = response.get("NextContinuationToken")
            if not isinstance(next_token, str) or not next_token:
                raise RuntimeError("Truncated S3 listing did not return continuation token.")
            token = next_token
        return tuple(sorted(values))


def _error_code(exc: BaseException) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, Mapping):
        return None
    error = response.get("Error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("Code")
    return None if code is None else str(code)
