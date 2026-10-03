from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.adapters.s3 import (
    S3ConditionalDatasetPublisher,
    S3ConditionalWriteCapabilityErrorV2,
    S3DatasetVersionStoreV2,
)


class _ProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class _IgnoringConditionalClient:
    """Fake S3 endpoint that accepts writes but ignores all conditional headers."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, dict[str, str], str]] = {}

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        bucket = str(kwargs["Bucket"])
        key = str(kwargs["Key"])
        body = bytes(kwargs["Body"])
        metadata = dict(kwargs.get("Metadata", {}))
        etag = f'"{hashlib.sha256(body).hexdigest()}"'
        self.objects[(bucket, key)] = (body, metadata, etag)
        return {"ETag": etag}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        try:
            body, metadata, etag = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ProviderError("NoSuchKey") from exc
        return {
            "Body": BytesIO(body),
            "Metadata": metadata,
            "ETag": etag,
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        try:
            _, metadata, etag = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ProviderError("NotFound") from exc
        return {"Metadata": metadata, "ETag": etag}

    def list_objects_v2(self, **kwargs: Any) -> dict[str, object]:
        bucket = str(kwargs["Bucket"])
        prefix = str(kwargs.get("Prefix", ""))
        return {
            "IsTruncated": False,
            "Contents": [
                {"Key": key}
                for (candidate_bucket, key) in self.objects
                if candidate_bucket == bucket and key.startswith(prefix)
            ],
        }

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        self.objects.pop((Bucket, Key), None)
        return {}


def test_s3_conditional_publication_fails_closed_when_endpoint_ignores_conditions() -> None:
    store = S3DatasetVersionStoreV2(
        bucket="lot26-fake",
        prefix="qualification",
        client=_IgnoringConditionalClient(),
    )

    with pytest.raises(
        S3ConditionalWriteCapabilityErrorV2,
        match="create-if-absent",
    ):
        S3ConditionalDatasetPublisher(
            store=store,
            ledger=MemoryPublicationLedger(),
        )
