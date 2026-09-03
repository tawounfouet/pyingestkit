from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

from pyingestkit.core.exceptions import PublicationError


class AtomicPublisher:
    """Atomic file publication on a single filesystem using os.replace()."""

    def publish_file(self, candidate: str | Path, destination: str | Path) -> Path:
        source = Path(candidate)
        target = Path(destination)
        if not source.is_file():
            raise PublicationError(f"Candidate file does not exist: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.parent / f".{target.name}.{uuid4().hex}.tmp"
        try:
            shutil.copy2(source, temp)
            os.replace(temp, target)
        except Exception as exc:
            temp.unlink(missing_ok=True)
            raise PublicationError(f"Atomic publication failed: {exc}") from exc
        return target
