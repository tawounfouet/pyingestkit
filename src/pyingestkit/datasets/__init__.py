"""Portable V2 dataset references.

The V1 versioning package remains unchanged during the V2 transition. These
reference DTOs are the clean-slate boundary values used by later V2 lots.
"""

from pyingestkit.domain.datasets import DatasetReference, DatasetVersionReference

__all__ = [
    "DatasetReference",
    "DatasetVersionReference",
]
