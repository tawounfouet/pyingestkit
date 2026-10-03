from __future__ import annotations

from pyingestkit.adapters.filesystem import FileConditionalDatasetPublisher
from pyingestkit.ports.governance import ConditionalDatasetPublisher


def test_lot25_filesystem_adapter_implements_frozen_conditional_port() -> None:
    assert issubclass(FileConditionalDatasetPublisher, ConditionalDatasetPublisher)


def test_lot25_filesystem_adapter_stays_in_explicit_provider_namespace() -> None:
    assert FileConditionalDatasetPublisher.__module__ == (
        "pyingestkit.adapters.filesystem.conditional_publisher"
    )
