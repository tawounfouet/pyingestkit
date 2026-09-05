from __future__ import annotations

import os
from pathlib import Path

from pyingestkit.config.models import ArtifactBackend, ArtifactConfig
from pyingestkit.core.exceptions import ConfigurationError

from .base import ArtifactStore
from .filesystem import LocalArtifactStore
from .s3 import S3ArtifactStore


def create_artifact_store(config: ArtifactConfig, *, workspace: str | Path) -> ArtifactStore:
    if config.backend is ArtifactBackend.LOCAL:
        return LocalArtifactStore(workspace)

    s3 = config.s3
    if s3.bucket is None:
        raise ConfigurationError("S3 artifact backend requires artifacts.s3.bucket")
    endpoint_url = None
    if s3.endpoint_url_env:
        endpoint_url = os.getenv(s3.endpoint_url_env)
    return S3ArtifactStore(
        bucket=s3.bucket,
        prefix=s3.prefix,
        cache_root=s3.cache_path or workspace,
        region_name=s3.region_name,
        endpoint_url=endpoint_url,
    )
