"""Filesystem CSV materializer for externally produced V2 dataset resources."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

from pyingestkit.adapters.formats.csv import CsvDecoderConfig, _decode_csv_bytes
from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import (
    DatasetVersion,
    DatasetVersionReference,
    dataset_content_fingerprint,
)
from pyingestkit.domain.datasets.materialization import ResourceDatasetVersionRequestV2


class FileCsvDatasetVersionMaterializerV2:
    """Promote a bounded local CSV resource without pretending it is ingestion RAW."""

    def __init__(
        self,
        *,
        allowed_roots: tuple[str | Path, ...],
        config: CsvDecoderConfig | None = None,
    ) -> None:
        if not isinstance(allowed_roots, tuple) or not allowed_roots:
            raise ValueError(
                "FileCsvDatasetVersionMaterializerV2 allowed_roots must be non-empty."
            )
        self._roots = tuple(Path(root).expanduser().resolve() for root in allowed_roots)
        self._config = config or CsvDecoderConfig()

    def materialize(
        self,
        request: ResourceDatasetVersionRequestV2,
    ) -> DatasetVersion:
        if not isinstance(request, ResourceDatasetVersionRequestV2):
            raise TypeError(
                "FileCsvDatasetVersionMaterializerV2 requires "
                "ResourceDatasetVersionRequestV2."
            )
        resource = request.resource
        if resource.locator is None:
            raise ValueError("File CSV materialization requires a concrete locator.")
        parsed = urlsplit(resource.locator)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            raise ValueError("File CSV materialization requires a local file:// resource.")
        if resource.format not in {None, "csv"}:
            raise ValueError("File CSV materialization requires format='csv' when provided.")
        if resource.media_type not in {None, "text/csv", "application/csv"}:
            raise ValueError("File CSV materialization requires a CSV media type.")

        raw_path = Path(url2pathname(unquote(parsed.path))).expanduser()
        if raw_path.is_symlink():
            raise ValueError("File CSV materialization rejects symbolic-link resources.")
        path = raw_path.resolve(strict=True)
        if not path.is_file():
            raise ValueError("File CSV materialization requires a regular file.")
        if not any(path.is_relative_to(root) for root in self._roots):
            raise ValueError("File CSV materialization resource escapes allowed roots.")

        content = path.read_bytes()
        representation, schema = _decode_csv_bytes(content, self._config)
        content_fingerprint = dataset_content_fingerprint(representation)
        checksum = hashlib.sha256(content).hexdigest()
        artifact = ArtifactReference(
            artifact_id=f"transform_{checksum}",
            kind="transformation_output",
            resource=resource,
            checksum=checksum,
            checksum_algorithm="sha256",
            media_type=resource.media_type or "text/csv",
            size_bytes=len(content),
            created_at=request.created_at,
            metadata=request.provenance,
        )
        reference = DatasetVersionReference(
            dataset_id=request.dataset_id,
            version_id=content_fingerprint,
            created_at=request.created_at,
            schema_fingerprint=schema.fingerprint,
            content_fingerprint=content_fingerprint,
            artifact_reference=artifact,
            locator=resource,
            metadata=request.provenance,
        )
        return DatasetVersion(
            reference=reference,
            source_artifact=artifact,
            ingestion_run_id=request.ingestion_run_id,
            decoder_id="csv",
            schema=schema,
            representation=representation,
        )
