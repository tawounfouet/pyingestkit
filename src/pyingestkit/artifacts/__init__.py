from typing import TYPE_CHECKING

from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactKind,
    ArtifactPutStatus,
    ArtifactReference,
    ArtifactRetention,
    PutArtifactRequest,
    PutArtifactResult,
    RawArtifactEvidence,
    RawPolicy,
)
from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore

if TYPE_CHECKING:
    from .factory import create_artifact_store as create_artifact_store
    from .filesystem import LocalArtifactStore as LocalArtifactStore
    from .raw import RawArtifact as RawArtifact
    from .s3 import S3ArtifactStore as S3ArtifactStore
    from .stored import StoredArtifact as StoredArtifact
    from .uri import ArtifactURI as ArtifactURI

__all__ = [
    "ArtifactIntegrityError",
    "ArtifactKind",
    "ArtifactPutStatus",
    "ArtifactReader",
    "ArtifactReference",
    "ArtifactRetention",
    "ArtifactStore",
    "PutArtifactRequest",
    "PutArtifactResult",
    "RawArtifactEvidence",
    "RawPolicy",
]


def __getattr__(name: str) -> object:
    if name == "S3ArtifactStore":
        from .s3 import S3ArtifactStore

        return S3ArtifactStore
    if name == "ArtifactURI":
        from .uri import ArtifactURI

        return ArtifactURI
    if name == "LocalArtifactStore":
        from .filesystem import LocalArtifactStore

        return LocalArtifactStore
    if name == "create_artifact_store":
        from .factory import create_artifact_store

        return create_artifact_store
    if name == "RawArtifact":
        from .raw import RawArtifact

        return RawArtifact
    if name == "StoredArtifact":
        from .stored import StoredArtifact

        return StoredArtifact
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
