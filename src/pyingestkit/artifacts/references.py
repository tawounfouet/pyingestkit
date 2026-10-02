"""V2 portable artifact reference.

This qualified module avoids changing the governed V1 `pyingestkit.artifacts`
`__all__` contract before the V2 root transition.
"""

from pyingestkit.domain.artifacts import ArtifactReference

__all__ = ["ArtifactReference"]
