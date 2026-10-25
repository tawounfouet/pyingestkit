"""Default implementation of V2 replay provenance resolution and historical reconstruction."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.replay import ReplayRequest
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank
from pyingestkit.domain.sources import Source
from pyingestkit.ports.artifacts import ArtifactStore
from pyingestkit.ports.dataset_versions import DatasetVersionStore
from pyingestkit.ports.replay import ReplayProvenanceResolver

_SENSITIVE_KEY_SUBSTRINGS = ("password", "secret", "token", "key", "auth", "credential")
_REDACTED_VALUE = "[REDACTED]"


def sanitize_parameter_overrides(parameters: Mapping[str, Any]) -> dict[str, str]:
    """Return a sanitized string dictionary of parameters redacting sensitive tokens."""
    sanitized: dict[str, str] = {}
    for key, value in parameters.items():
        key_str = str(key)
        lower_key = key_str.lower()
        if any(substr in lower_key for substr in _SENSITIVE_KEY_SUBSTRINGS):
            sanitized[key_str] = _REDACTED_VALUE
        else:
            sanitized[key_str] = str(value)
    return sanitized


class DefaultReplayProvenanceResolver(ReplayProvenanceResolver):
    """Resolve durable historical version and run evidence into executable ReplayRequests."""

    def __init__(
        self,
        *,
        version_store: DatasetVersionStore,
        artifact_store: ArtifactStore,
        definitions: Mapping[str, IngestionDefinition] | None = None,
        runs: Mapping[IngestionRunId, tuple[IngestionDefinition, ArtifactReference]] | None = None,
    ) -> None:
        if not isinstance(version_store, DatasetVersionStore):
            raise TypeError("DefaultReplayProvenanceResolver requires a DatasetVersionStore.")
        if not isinstance(artifact_store, ArtifactStore):
            raise TypeError("DefaultReplayProvenanceResolver requires an ArtifactStore.")
        self._version_store = version_store
        self._artifact_store = artifact_store
        self._definitions = dict(definitions) if definitions is not None else {}
        self._runs = dict(runs) if runs is not None else {}

    def register_definition(self, definition: IngestionDefinition) -> None:
        """Register a known IngestionDefinition by name."""
        if not isinstance(definition, IngestionDefinition):
            raise TypeError("register_definition requires IngestionDefinition.")
        self._definitions[definition.name] = definition

    def register_run(
        self,
        run_id: IngestionRunId,
        definition: IngestionDefinition,
        raw_artifact: ArtifactReference,
    ) -> None:
        """Register known historical run context."""
        if not isinstance(run_id, IngestionRunId):
            raise TypeError("register_run requires IngestionRunId.")
        if not isinstance(definition, IngestionDefinition):
            raise TypeError("register_run requires IngestionDefinition.")
        if not isinstance(raw_artifact, ArtifactReference):
            raise TypeError("register_run requires ArtifactReference.")
        if raw_artifact.kind != "raw":
            raise ValueError("register_run requires a RAW ArtifactReference.")
        self._runs[run_id] = (definition, raw_artifact)

    def resolve_from_version(
        self,
        dataset_id: str,
        version_id: str,
        *,
        parameter_overrides: Mapping[str, object] | None = None,
    ) -> ReplayRequest:
        """Resolve a historical version into a strict ReplayRequest."""
        require_non_blank(dataset_id, "dataset_id")
        require_non_blank(version_id, "version_id")

        version_ref = self._version_store.get(dataset_id, version_id)
        meta_dict = dict(version_ref.metadata)

        # 1. Resolve source_run_id
        source_run_id_raw = meta_dict.get("source_run_id")
        if source_run_id_raw is not None:
            source_run_id = IngestionRunId.parse(source_run_id_raw)
        else:
            source_run_id = IngestionRunId.new()

        # 2. Resolve origin_raw_artifact
        origin_raw: ArtifactReference | None = None
        if (
            version_ref.artifact_reference is not None
            and version_ref.artifact_reference.kind == "raw"
        ):
            origin_raw = version_ref.artifact_reference
        elif source_run_id in self._runs:
            origin_raw = self._runs[source_run_id][1]
        elif "source_raw_artifact_id" in meta_dict:
            raw_id = meta_dict["source_raw_artifact_id"]
            raw_checksum = meta_dict.get(
                "source_raw_checksum", version_ref.content_fingerprint or ""
            )
            raw_locator = meta_dict.get("source_raw_locator", f"memory://artifacts/{raw_id}")
            raw_namespace = meta_dict.get("source_raw_namespace")
            raw_res_id = meta_dict.get("source_raw_resource_id")
            if not raw_namespace:
                if raw_locator.startswith("file://"):
                    raw_namespace = "pyingestkit.artifact.file"
                    raw_res_id = f"file_{hashlib.sha256(raw_locator.encode()).hexdigest()}"
                elif raw_locator.startswith("s3://"):
                    raw_namespace = "pyingestkit.artifact.s3"
                    raw_res_id = f"s3_{hashlib.sha256(raw_locator.encode()).hexdigest()}"
                else:
                    raw_namespace = "pyingestkit.replay"
                    raw_res_id = raw_id
            origin_raw = ArtifactReference(
                artifact_id=raw_id,
                kind="raw",
                resource=ResourceReference(
                    namespace=raw_namespace,
                    resource_id=raw_res_id or raw_id,
                    locator=raw_locator,
                ),
                checksum_algorithm="sha256",
                checksum=raw_checksum,
                metadata=(("source_run_id", str(source_run_id)),),
            )

        if origin_raw is None:
            raise LookupError(
                f"Cannot resolve origin RAW artifact for dataset '{dataset_id}' version '{version_id}'. "
                "The version metadata contains no RAW artifact reference."
            )

        # 3. Resolve IngestionDefinition
        def_name = meta_dict.get("definition_name", dataset_id)
        definition: IngestionDefinition | None = None
        if def_name in self._definitions:
            definition = self._definitions[def_name]
        elif source_run_id in self._runs:
            definition = self._runs[source_run_id][0]
        else:
            decoder_id = meta_dict.get("decoder_id", "json")
            definition = IngestionDefinition(
                name=def_name,
                source=Source.file(path=f"/historical-raw/{dataset_id}"),
                decoder=decoder_id,
                dataset=dataset_id,
            )

        # 4. Apply safe parameter overrides if provided
        if parameter_overrides:
            sanitized = sanitize_parameter_overrides(parameter_overrides)
            existing_options = dict(definition.options)
            existing_options.update(sanitized)
            definition = replace(definition, options=tuple(sorted(existing_options.items())))

        return ReplayRequest(
            source_run_id=source_run_id,
            definition=definition,
            origin_raw_artifact=origin_raw,
            expected_dataset_version=version_ref,
        )

    def resolve_from_run(
        self,
        source_run_id: IngestionRunId,
        *,
        parameter_overrides: Mapping[str, object] | None = None,
    ) -> ReplayRequest:
        """Resolve a historical run into a strict ReplayRequest."""
        if not isinstance(source_run_id, IngestionRunId):
            raise TypeError("resolve_from_run requires IngestionRunId.")

        if source_run_id not in self._runs:
            raise KeyError(f"No recorded historical run found for {source_run_id}")

        definition, origin_raw = self._runs[source_run_id]

        if parameter_overrides:
            sanitized = sanitize_parameter_overrides(parameter_overrides)
            existing_options = dict(definition.options)
            existing_options.update(sanitized)
            definition = replace(definition, options=tuple(sorted(existing_options.items())))

        return ReplayRequest(
            source_run_id=source_run_id,
            definition=definition,
            origin_raw_artifact=origin_raw,
        )


__all__ = ["DefaultReplayProvenanceResolver", "sanitize_parameter_overrides"]
