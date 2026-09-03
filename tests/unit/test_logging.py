from __future__ import annotations

import json
import logging
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from pyingestkit.config import FileLoggingConfig, LoggingConfig, LogOutputFormat
from pyingestkit.logging import configure_logging, log_context, redact_mapping, redact_text


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
        for secret in ("hunter2", "abc", "xyz", "secret-token"):
            self.assertNotIn(secret, redacted)
        self.assertGreaterEqual(redacted.count("***REDACTED***"), 4)

    def test_redacts_secret_runtime_parameter_keys(self) -> None:
        self.assertEqual(
            redact_mapping({"token": "abc", "nested": {"password": "x", "safe": 1}}),
            {"token": "***REDACTED***", "nested": {"password": "***REDACTED***", "safe": 1}},
        )

    def test_json_file_logging_contains_full_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "pyingest.log"
            config = LoggingConfig(
                console=False,
                file=FileLoggingConfig(
                    enabled=True,
                    path=log_path,
                    level="INFO",
                    format=LogOutputFormat.JSON,
                ),
            )
            configure_logging(config)
            logger = logging.getLogger("pyingestkit.tests.logging")
            run_id = "785c1cdc-3735-4a0b-97d7-304bb2702a80"
            with log_context(run_id=run_id, job_id="demo.job", step="FetchLocal"):
                logger.info("downloaded token=super-secret")
            payload = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["run_id"], run_id)
            self.assertEqual(payload["job_id"], "demo.job")
            self.assertEqual(payload["step"], "FetchLocal")
            self.assertIn("+00:00", payload["timestamp"])
            self.assertNotIn("super-secret", payload["message"])

    def test_plain_terminal_format_has_local_timestamp_and_short_run_id(self) -> None:
        stream = StringIO()
        original_stderr = __import__("sys").stderr
        try:
            __import__("sys").stderr = stream
            configure_logging(
                LoggingConfig(level="INFO", format=LogOutputFormat.PLAIN, console=True)
            )
            with log_context(
                run_id="785c1cdc-3735-4a0b-97d7-304bb2702a80",
                job_id="demo.local_file",
                step="FetchLocal",
            ):
                logging.getLogger("pyingestkit.tests.logging").info("Step started")
        finally:
            __import__("sys").stderr = original_stderr
        output = stream.getvalue()
        self.assertRegex(output, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        self.assertIn("INFO", output)
        self.assertIn("[run=785c1cdc job=demo.local_file step=FetchLocal]", output)
        self.assertNotIn("785c1cdc-3735", output)

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
