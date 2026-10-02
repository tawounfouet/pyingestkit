from pyingestkit.domain.artifacts import ArtifactReference, RawPolicy

from .base import ArtifactStore
from .factory import create_artifact_store
from .filesystem import LocalArtifactStore
from .raw import RawArtifact
from .s3 import S3ArtifactStore
from .stored import StoredArtifact
from .uri import ArtifactURI

__all__ = [
    "ArtifactStore",
    "ArtifactURI",
    "LocalArtifactStore",
    "RawArtifact",
    "S3ArtifactStore",
    "StoredArtifact",
    "create_artifact_store",
]

# V2 transition: explicit imports are available while the exact V1 __all__
# contract remains unchanged until the 2.0 alpha package line is cut.
_V2_PROVISIONAL = {
    "ArtifactReference": ArtifactReference,
    "RawPolicy": RawPolicy,
}
