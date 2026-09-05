"""Public deprecation helpers used by PyIngestKit and extension packages."""

from __future__ import annotations

import warnings


class PyIngestKitDeprecationWarning(FutureWarning):
    """Visible-by-default warning for public PyIngestKit deprecations."""


def warn_deprecated(
    feature: str,
    *,
    replacement: str | None = None,
    removal: str | None = None,
    stacklevel: int = 2,
) -> None:
    """Emit the canonical V1 deprecation warning.

    ``FutureWarning`` semantics are intentional: user-facing configuration,
    CLI and plugin deprecations should be visible in ordinary application
    execution rather than hidden by Python's default ``DeprecationWarning``
    filter.
    """

    message = f"{feature} is deprecated"
    if replacement:
        message += f"; use {replacement} instead"
    if removal:
        message += f"; scheduled for removal in {removal}"
    warnings.warn(message, PyIngestKitDeprecationWarning, stacklevel=stacklevel)


__all__ = ["PyIngestKitDeprecationWarning", "warn_deprecated"]
