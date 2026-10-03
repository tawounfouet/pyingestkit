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

    def delete_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]: ...


def validate_s3_endpoint_v2(endpoint_url: str | None) -> None:
    """Validate an optional S3-compatible endpoint without performing I/O."""
    if endpoint_url is None:
        return
    parsed = urlsplit(endpoint_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("S3 endpoint URL must not embed credentials.")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("S3 endpoint URL must be absolute HTTP(S).")


def create_s3_client_v2(
    *,
    region_name: str | None,
    endpoint_url: str | None,
) -> S3ClientV2:
    """Create the optional boto3 client only when a caller actually needs it."""
    validate_s3_endpoint_v2(endpoint_url)
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


class S3ConditionalWriteConflictV2(RuntimeError):
    """Provider rejected a stale/duplicate conditional object write."""


class S3ConditionalWriteCapabilityErrorV2(RuntimeError):
    """Endpoint did not prove the conditional-write profile required by LOT-26."""


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
        if normalized_prefix and any(
            part in {"", ".", ".."} for part in normalized_prefix.split("/")
        ):
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
        return _validated_body(response)

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        """Read one object together with its provider token for internal CAS use."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            if _error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise KeyError(key) from exc
            raise RuntimeError("Unable to read S3 object for conditional publication.") from exc
        content = _validated_body(response)
        etag = response.get("ETag")
        if not isinstance(etag, str) or not etag.strip():
            raise RuntimeError("S3 object response is missing a usable ETag.")
        return content, etag

    def put_if_absent(
        self,
        key: str,
        content: bytes,
        *,
        kind: str,
        content_type: str | None = None,
    ) -> str:
        return self._put_conditional(
            key,
            content,
            kind=kind,
            content_type=content_type,
            if_none_match="*",
        )

    def put_if_match(
        self,
        key: str,
        content: bytes,
        *,
        expected_etag: str,
        kind: str,
        content_type: str | None = None,
    ) -> str:
        if not isinstance(expected_etag, str) or not expected_etag.strip():
            raise ValueError("expected_etag must be non-blank.")
        return self._put_conditional(
            key,
            content,
            kind=kind,
            content_type=content_type,
            if_match=expected_etag,
        )

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            raise RuntimeError("Unable to delete S3 object.") from exc

    def qualify_conditional_writes(self, *, probe_key: str) -> None:
        """Prove the endpoint's create-if-absent and compare-and-replace semantics."""
        first = b"pyingestkit-cas-probe-v1"
        second = b"pyingestkit-cas-probe-v2"
        third = b"pyingestkit-cas-probe-stale"
        try:
            initial_etag = self.put_if_absent(
                probe_key,
                first,
                kind="conditional-publication-probe",
                content_type="application/octet-stream",
            )
            try:
                self.put_if_absent(
                    probe_key,
                    second,
                    kind="conditional-publication-probe",
                    content_type="application/octet-stream",
                )
            except S3ConditionalWriteConflictV2:
                pass
            else:
                raise S3ConditionalWriteCapabilityErrorV2(
                    "Endpoint did not enforce atomic create-if-absent."
                )

            observed, observed_etag = self.read_with_etag(probe_key)
            if observed != first:
                raise S3ConditionalWriteCapabilityErrorV2(
                    "Endpoint changed probe bytes after rejected create-if-absent."
                )
            if observed_etag != initial_etag:
                initial_etag = observed_etag

            replacement_etag = self.put_if_match(
                probe_key,
                second,
                expected_etag=initial_etag,
                kind="conditional-publication-probe",
                content_type="application/octet-stream",
            )
            try:
                self.put_if_match(
                    probe_key,
                    third,
                    expected_etag=initial_etag,
                    kind="conditional-publication-probe",
                    content_type="application/octet-stream",
                )
            except S3ConditionalWriteConflictV2:
                pass
            else:
                raise S3ConditionalWriteCapabilityErrorV2(
                    "Endpoint did not reject a stale compare-and-replace token."
                )

            final, final_etag = self.read_with_etag(probe_key)
            if final != second or final_etag != replacement_etag:
                raise S3ConditionalWriteCapabilityErrorV2(
                    "Endpoint conditional replacement could not be reconciled from provider truth."
                )
        except S3ConditionalWriteConflictV2 as exc:
            raise S3ConditionalWriteCapabilityErrorV2(
                "Endpoint probe key unexpectedly conflicted during first creation."
            ) from exc
        except S3ConditionalWriteCapabilityErrorV2:
            raise
        except (RuntimeError, ValueError) as exc:
            raise S3ConditionalWriteCapabilityErrorV2(
                "Endpoint failed the conditional-write capability probe."
            ) from exc
        finally:
            try:
                self.delete(probe_key)
            except RuntimeError:
                pass

    def _put_conditional(
        self,
        key: str,
        content: bytes,
        *,
        kind: str,
        content_type: str | None,
        if_none_match: str | None = None,
        if_match: str | None = None,
    ) -> str:
        if (if_none_match is None) == (if_match is None):
            raise ValueError("Exactly one S3 conditional write precondition is required.")
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
        if if_none_match is not None:
            request["IfNoneMatch"] = if_none_match
        if if_match is not None:
            request["IfMatch"] = if_match
        try:
            response = self.client.put_object(**request)
        except Exception as exc:  # noqa: BLE001 - optional provider boundary
            if _error_code(exc) in {
                "409",
                "412",
                "ConditionalRequestConflict",
                "PreconditionFailed",
            }:
                raise S3ConditionalWriteConflictV2("S3 conditional write conflicted.") from exc
            raise RuntimeError("Unable to perform conditional S3 object write.") from exc
        etag = response.get("ETag")
        if not isinstance(etag, str) or not etag.strip():
            head = self.head(key)
            etag = None if head is None else head.get("ETag")
        if not isinstance(etag, str) or not etag.strip():
            raise RuntimeError("Conditional S3 write did not return a usable ETag.")
        return etag

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


def _validated_body(response: Mapping[str, Any]) -> bytes:
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
