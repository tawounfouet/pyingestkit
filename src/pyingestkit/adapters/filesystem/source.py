"""Local filesystem source connector for the V2 reference profile."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.sources import SourceKind
from pyingestkit.ports.sources import (
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)

_DEFAULT_MAX_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FileAccessPolicy:
    """Bounded filesystem policy applied only when acquisition is executed."""

    allowed_roots: tuple[Path, ...]
    max_bytes: int = _DEFAULT_MAX_BYTES
    allowed_extensions: tuple[str, ...] = ()
    allow_symlinks: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_roots, tuple):
            raise TypeError("FileAccessPolicy allowed_roots must be a tuple.")
        if not self.allowed_roots:
            raise ValueError("FileAccessPolicy requires at least one allowed root.")
        if any(not isinstance(root, Path) for root in self.allowed_roots):
            raise TypeError("FileAccessPolicy allowed_roots must contain pathlib.Path values.")
        if not isinstance(self.max_bytes, int):
            raise TypeError("FileAccessPolicy max_bytes must be an int.")
        if self.max_bytes < 1:
            raise ValueError("FileAccessPolicy max_bytes must be >= 1.")
        if not isinstance(self.allowed_extensions, tuple):
            raise TypeError("FileAccessPolicy allowed_extensions must be a tuple.")
        for extension in self.allowed_extensions:
            if not isinstance(extension, str) or not extension.strip():
                raise ValueError("FileAccessPolicy extensions must be non-empty strings.")
        if not isinstance(self.allow_symlinks, bool):
            raise TypeError("FileAccessPolicy allow_symlinks must be bool.")

    @property
    def normalized_extensions(self) -> frozenset[str]:
        return frozenset(
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in self.allowed_extensions
        )


class _FileAccessError(Exception):
    def __init__(
        self,
        *,
        code: str,
        category: FailureCategory,
        summary: str,
        retryability: Retryability = Retryability.NON_RETRYABLE,
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.category = category
        self.summary = summary
        self.retryability = retryability


class FileSourceConnector:
    """Stateless synchronous local-file connector.

    The connector owns no open file handles between calls. Construction performs
    no filesystem access; configured roots are validated only by acquire().
    """

    _DESCRIPTOR = SourceConnectorDescriptor(
        id="pyingestkit.file",
        display_name="Local file",
        connector_version="1",
        supported_source_kinds=(SourceKind.FILE,),
        capabilities=(SourceConnectorCapability.ACQUIRE,),
        optional_dependencies_available=True,
    )

    def __init__(self, *, policy: FileAccessPolicy) -> None:
        if not isinstance(policy, FileAccessPolicy):
            raise TypeError("FileSourceConnector policy must be a FileAccessPolicy.")
        self._policy = policy

    @property
    def descriptor(self) -> SourceConnectorDescriptor:
        return self._DESCRIPTOR

    @property
    def policy(self) -> FileAccessPolicy:
        return self._policy

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        if not isinstance(request, AcquisitionRequest):
            raise TypeError("FileSourceConnector.acquire expects AcquisitionRequest.")
        if request.source.kind is not SourceKind.FILE:
            raise ValueError("FileSourceConnector only supports SourceKind.FILE.")
        assert request.source.locator is not None

        try:
            path = self._resolve_path(request.source.locator)
            self._validate_extension(path)
            stat = path.stat()
            if stat.st_size > self._policy.max_bytes:
                raise _FileAccessError(
                    code="acquisition.file.too_large",
                    category=FailureCategory.RESOURCE_EXHAUSTED,
                    summary="Local source exceeds the configured acquisition limit.",
                )
            with path.open("rb") as handle:
                content = handle.read(self._policy.max_bytes + 1)
            if len(content) > self._policy.max_bytes:
                raise _FileAccessError(
                    code="acquisition.file.too_large",
                    category=FailureCategory.RESOURCE_EXHAUSTED,
                    summary="Local source exceeds the configured acquisition limit.",
                )
        except _FileAccessError as exc:
            return self._failed(
                request,
                code=exc.code,
                category=exc.category,
                retryability=exc.retryability,
                summary=exc.summary,
            )
        except PermissionError:
            return self._failed(
                request,
                code="acquisition.file.permission_denied",
                category=FailureCategory.AUTHORIZATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="Local source could not be read because access was denied.",
            )
        except OSError:
            return self._failed(
                request,
                code="acquisition.file.io_error",
                category=FailureCategory.EXTERNAL_PROVIDER,
                retryability=Retryability.UNKNOWN,
                summary="Local source acquisition failed during filesystem I/O.",
            )

        acquired_at = datetime.now(UTC)
        checksum = hashlib.sha256(content).hexdigest()
        uri = path.as_uri()
        media_type, _ = mimetypes.guess_type(path.name)
        resource = ResourceReference(
            namespace="pyingestkit.resource.file",
            resource_id=_resource_id(uri),
            locator=uri,
            media_type=media_type,
            format=path.suffix.lstrip(".").lower() or None,
            metadata=(("file_name", path.name),),
        )
        diagnostic = Diagnostic(
            code="acquisition.file.succeeded",
            severity=DiagnosticSeverity.INFO,
            summary="Local source acquisition completed.",
            stage="acquire",
            source_context="file",
            details=(
                ("checksum_algorithm", "sha256"),
                ("size_bytes", str(len(content))),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return AcquisitionResult(
            status=AcquisitionStatus.SUCCEEDED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            source_kind=SourceKind.FILE,
            acquired_at=acquired_at,
            resource=resource,
            content=content,
            checksum_algorithm="sha256",
            checksum=checksum,
            size_bytes=len(content),
            media_type=media_type,
            source_metadata=(
                ("file_name", path.name),
                ("mtime_ns", str(stat.st_mtime_ns)),
            ),
            diagnostics=(diagnostic,),
        )

    def _resolve_path(self, locator: str) -> Path:
        source_path = Path(locator).expanduser()
        configured_roots = self._configured_roots()

        eligible = False
        for configured_root, resolved_root in configured_roots:
            candidate = source_path if source_path.is_absolute() else configured_root / source_path
            lexical_candidate = Path(os.path.abspath(candidate))
            lexical_root = Path(os.path.abspath(configured_root))
            if not lexical_candidate.is_relative_to(lexical_root):
                continue
            eligible = True

            if not self._policy.allow_symlinks and _contains_symlink(
                lexical_root, lexical_candidate
            ):
                raise _FileAccessError(
                    code="acquisition.file.symlink_forbidden",
                    category=FailureCategory.AUTHORIZATION,
                    summary="Local source crosses a forbidden symbolic link.",
                )

            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue

            if not resolved.is_relative_to(resolved_root):
                raise _FileAccessError(
                    code="acquisition.file.outside_allowed_root",
                    category=FailureCategory.AUTHORIZATION,
                    summary="Local source resolves outside configured roots.",
                )
            if not resolved.is_file():
                raise _FileAccessError(
                    code="acquisition.file.not_regular_file",
                    category=FailureCategory.CONFIGURATION,
                    summary="Local source must resolve to a regular file.",
                )
            return resolved

        if eligible:
            raise _FileAccessError(
                code="acquisition.file.not_found",
                category=FailureCategory.NOT_FOUND,
                summary="Local source file was not found.",
            )
        raise _FileAccessError(
            code="acquisition.file.outside_allowed_root",
            category=FailureCategory.AUTHORIZATION,
            summary="Local source is outside configured roots.",
        )

    def _configured_roots(self) -> tuple[tuple[Path, Path], ...]:
        roots: list[tuple[Path, Path]] = []
        for configured in self._policy.allowed_roots:
            expanded = configured.expanduser()
            if not self._policy.allow_symlinks and expanded.is_symlink():
                raise _FileAccessError(
                    code="acquisition.file.symlink_root_forbidden",
                    category=FailureCategory.CONFIGURATION,
                    summary="Configured file root must not be a symbolic link.",
                )
            try:
                resolved = expanded.resolve(strict=True)
            except FileNotFoundError as exc:
                raise _FileAccessError(
                    code="acquisition.file.root_not_found",
                    category=FailureCategory.CONFIGURATION,
                    summary="Configured file root does not exist.",
                ) from exc
            if not resolved.is_dir():
                raise _FileAccessError(
                    code="acquisition.file.root_not_directory",
                    category=FailureCategory.CONFIGURATION,
                    summary="Configured file root must be a directory.",
                )
            roots.append((expanded, resolved))
        return tuple(roots)

    def _validate_extension(self, path: Path) -> None:
        allowed = self._policy.normalized_extensions
        if allowed and path.suffix.lower() not in allowed:
            raise _FileAccessError(
                code="acquisition.file.extension_forbidden",
                category=FailureCategory.CONFIGURATION,
                summary="Local source extension is not allowed by policy.",
            )

    @staticmethod
    def _failed(
        request: AcquisitionRequest,
        *,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
    ) -> AcquisitionResult:
        failure = FailureEvidence(
            error_code=code,
            category=category,
            retryability=retryability,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
            source_component="file_source_connector",
            message_summary=summary,
        )
        diagnostic = Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            summary=summary,
            stage="acquire",
            source_context="file",
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return AcquisitionResult(
            status=AcquisitionStatus.FAILED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            source_kind=SourceKind.FILE,
            diagnostics=(diagnostic,),
            failure=failure,
        )


def _contains_symlink(root: Path, candidate: Path) -> bool:
    if root.is_symlink():
        return True
    relative = candidate.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _resource_id(uri: str) -> str:
    digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
    return f"file_{digest}"
