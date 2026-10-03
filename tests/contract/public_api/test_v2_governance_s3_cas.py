from __future__ import annotations

from pyingestkit.adapters.s3 import (
    S3ConditionalDatasetPublisher,
    S3ConditionalWriteCapabilityErrorV2,
)
from pyingestkit.ports.governance import ConditionalDatasetPublisher


def test_lot26_s3_adapter_implements_frozen_conditional_port() -> None:
    assert issubclass(S3ConditionalDatasetPublisher, ConditionalDatasetPublisher)


def test_lot26_s3_adapter_stays_in_explicit_provider_namespace() -> None:
    assert S3ConditionalDatasetPublisher.__module__ == (
        "pyingestkit.adapters.s3.conditional_publisher"
    )


def test_lot26_capability_failure_is_provider_specific_not_domain_surface() -> None:
    assert issubclass(S3ConditionalWriteCapabilityErrorV2, RuntimeError)
    assert S3ConditionalWriteCapabilityErrorV2.__module__ == ("pyingestkit.adapters.s3._objects")
