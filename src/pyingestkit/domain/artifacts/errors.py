"""Artifact-domain errors exposed by the V2 storage boundary."""

from __future__ import annotations


class ArtifactIntegrityError(RuntimeError):
    """Raised when durable artifact bytes no longer match their reference evidence."""
