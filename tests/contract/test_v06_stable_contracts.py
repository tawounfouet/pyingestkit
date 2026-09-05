from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from pyingestkit.config.models import ArtifactConfig, S3ArtifactConfig
from pyingestkit.core.exceptions import (
    IngestionError,
    ReplayError,
    ReplayIntegrityError,
    ReplayMismatchError,
    StorageError,
    VersionStoreError,
)


def test_v06_s3_config_contract_is_frozen_and_secret_free() -> None:
    assert set(S3ArtifactConfig.model_fields) == {
        "bucket",
        "prefix",
        "region_name",
        "endpoint_url_env",
        "cache_path",
    }
    assert set(ArtifactConfig.model_fields) == {"backend", "s3"}
    lowered = {name.lower() for name in S3ArtifactConfig.model_fields}
    assert not any(token in name for name in lowered for token in ("password", "secret", "token", "access_key"))

    try:
        S3ArtifactConfig(bucket="bucket", access_key="forbidden")  # type: ignore[call-arg]
    except PydanticValidationError:
        pass
    else:
        raise AssertionError("V0.6 S3 configuration must reject inline credentials/unknown fields")


def test_v06_storage_and_replay_error_hierarchy_is_frozen() -> None:
    assert issubclass(StorageError, IngestionError)
    assert issubclass(VersionStoreError, IngestionError)
    assert issubclass(ReplayError, IngestionError)
    assert issubclass(ReplayIntegrityError, ReplayError)
    assert issubclass(ReplayMismatchError, ReplayError)
