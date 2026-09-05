from __future__ import annotations

from dataclasses import replace

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from pyingestkit.artifacts.raw import RawArtifact

from ._schema import artifact_locations
from .models import ArtifactRecord


def record_artifact_location(engine: Engine, artifact: RawArtifact) -> None:
    """Persist the portable storage URI after the legacy artifact row exists."""

    with engine.begin() as connection:
        existing = connection.execute(
            select(artifact_locations.c.artifact_id).where(
                artifact_locations.c.artifact_id == artifact.artifact_id
            )
        ).scalar_one_or_none()
        if existing is None:
            connection.execute(
                insert(artifact_locations).values(
                    artifact_id=artifact.artifact_id,
                    storage_uri=str(artifact.location_uri),
                    local_path=artifact.path,
                )
            )


def enrich_artifact_locations(
    engine: Engine,
    records: tuple[ArtifactRecord, ...],
) -> tuple[ArtifactRecord, ...]:
    if not records:
        return records
    ids = [record.artifact_id for record in records]
    with engine.connect() as connection:
        rows = connection.execute(
            select(artifact_locations.c.artifact_id, artifact_locations.c.storage_uri).where(
                artifact_locations.c.artifact_id.in_(ids)
            )
        ).all()
    locations = {str(row[0]): str(row[1]) for row in rows}
    return tuple(
        replace(record, storage_uri=locations.get(record.artifact_id)) for record in records
    )
