"""Optional PyTransformKit integration boundary.

The module is importable without PyTransformKit installed. Provider contracts
are loaded only when an integration operation is invoked.
"""

from pyingestkit.integrations.pytransformkit.adapters import (
    DatasetVersionInputAdapter,
    PyTransformKitCompatibilityError,
    PyTransformKitIntegrationError,
    PyTransformKitMappingError,
    PyTransformKitUnavailableError,
    TransformationPublicationAdapter,
    TransformationPublicationInput,
    from_transform_correlation,
    from_transform_failure,
    pytransformkit_version,
    to_transform_correlation,
)

__all__ = [
    "DatasetVersionInputAdapter",
    "PyTransformKitCompatibilityError",
    "PyTransformKitIntegrationError",
    "PyTransformKitMappingError",
    "PyTransformKitUnavailableError",
    "TransformationPublicationAdapter",
    "TransformationPublicationInput",
    "from_transform_correlation",
    "from_transform_failure",
    "pytransformkit_version",
    "to_transform_correlation",
]
