from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from pyingestkit.config import FileLoggingConfig, LoggingConfig, LogOutputFormat
from pyingestkit.logging import configure_logging, log_context, redact_text


class LoggingTests(unittest.TestCase):
    def tearDown(self) -> None:
        root = logging.getLogger()
        for handler in tuple(root.handlers):
            root.removeHandler(handler)
            handler.close()
        root.setLevel(logging.WARNING)

    def test_redacts_common_secret_patterns(self) -> None:
        text = "password=hunter2 token: abc api_key=xyz Authorization: Bearer secret-token"
        redacted = redact_text(text)
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("abc", redacted)
        self.assertNotIn("xyz", redacted)
        self.assertNotIn("secret-token", redacted)
        self.assertGreaterEqual(redacted.count("***REDACTED***"), 4)

    def test_json_file_logging_contains_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "pyingest.log"
            config = LoggingConfig(
                console=False,
                file=FileLoggingConfig(
                    enabled=True,
                    path=log_path,
                    level="INFO",
                    format=LogOutputFormat.JSON,
                    max_bytes=100_000,
                    backup_count=1,
                ),
            )
            configure_logging(config)
            logger = logging.getLogger("pyingestkit.tests.logging")
            with log_context(run_id="run-123", job_id="demo.job", step="FetchLocal"):
                logger.info("downloaded token=super-secret")

            payload = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["level"], "INFO")
            self.assertEqual(payload["run_id"], "run-123")
            self.assertEqual(payload["job_id"], "demo.job")
            self.assertEqual(payload["step"], "FetchLocal")
            self.assertNotIn("super-secret", payload["message"])
            self.assertIn("***REDACTED***", payload["message"])

    def test_plain_file_logging_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "pyingest.log"
            configure_logging(
                LoggingConfig(
                    console=False,
                    file=FileLoggingConfig(
                        enabled=True,
                        path=log_path,
                        level="DEBUG",
                        format=LogOutputFormat.PLAIN,
                    ),
                )
            )
            logging.getLogger("pyingestkit.tests.logging").debug("plain log works")
            self.assertIn("plain log works", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
