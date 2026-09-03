from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.sources import LocalSource

logger = logging.getLogger(__name__)


class FetchLocal(Step):
    """Fetch the local file declared through the runtime ``path`` parameter."""

    def execute(self, context: RunContext, data: Any) -> Any:
        raw_path = context.parameter("path")
        if raw_path in (None, ""):
            raise ConfigurationError(
                "demo.local_file requires runtime parameter 'path'. "
                "Set it in pyingest.yml or pass --param path=<file>."
            )
        logger.debug("Demo plugin fetching local source path=%s", raw_path)
        return LocalSource(Path(str(raw_path))).fetch(context)


class DemoLocalFileJob(Job):
    id = "demo.local_file"
    version = "0.1.0"
    description = "Demonstration job that ingests a local file into immutable RAW storage."

    def pipeline(self) -> Pipeline:
        return Pipeline([FetchLocal()])


job = DemoLocalFileJob()
