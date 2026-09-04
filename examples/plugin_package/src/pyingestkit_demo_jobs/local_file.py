from __future__ import annotations

import logging
from pathlib import Path

from pyingestkit import RunContext, job, step
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.sources import LocalSource

logger = logging.getLogger(__name__)


@step(name="FetchLocal")
def fetch_local(context: RunContext):
    """Fetch the local file declared through runtime parameter ``path``."""
    raw_path = context.parameter("path")
    if raw_path in (None, ""):
        raise ConfigurationError(
            "demo.local_file requires runtime parameter 'path'. "
            "Set it in pyingest.yml or pass --param path=<file>."
        )
    logger.debug("Demo plugin fetching local source path=%s", raw_path)
    return LocalSource(Path(str(raw_path))).fetch(context)


@job(
    id="demo.local_file",
    version="0.4.0",
    description="Demonstration job that ingests a local file into immutable RAW storage.",
)
def local_file_job() -> None:
    fetch_local()


# Entry-point friendly alias. Exposes a JobDefinition, not a runtime instance.
job_definition = local_file_job
# Backward-compatible example alias retained for V0.1.x callers.
job = local_file_job
