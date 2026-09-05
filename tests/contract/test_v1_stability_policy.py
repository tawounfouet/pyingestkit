from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError as PydanticValidationError
from typer.testing import CliRunner

import pyingestkit.errors as errors
from pyingestkit import Job, Pipeline
from pyingestkit.cli.app import app
from pyingestkit.cli.main import _load_local_dotenv
from pyingestkit.config import FileLoggingConfig, LogOutputFormat, PyIngestKitConfig, load_config
from pyingestkit.core.exceptions import ConfigurationError, PluginError
from pyingestkit.deprecations import PyIngestKitDeprecationWarning, warn_deprecated
from pyingestkit.logging import configure_logging, log_context, redact_text
from pyingestkit.plugins.discovery import discover_jobs, discover_plugins

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "contract" / "fixtures" / "stability_v1.json"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


class _Healthy(Job):
    id = "demo.same"

    def pipeline(self) -> Pipeline:
        return Pipeline([])


class _SecondHealthy(Job):
    id = "demo.same"

    def pipeline(self) -> Pipeline:
        return Pipeline([])


class _EntryPoint:
    def __init__(self, name: str, value_name: str, loaded: object) -> None:
        self.name = name
        self.value = value_name
        self._loaded = loaded

    def load(self) -> object:
        if isinstance(self._loaded, BaseException):
            raise self._loaded
        return self._loaded


class _EntryPoints:
    def __init__(self, values: list[_EntryPoint]) -> None:
        self.values = values

    def select(self, *, group: str) -> tuple[_EntryPoint, ...]:
        assert group == "pyingestkit.jobs"
        return tuple(self.values)


def test_b1_contract_is_versioned_and_anchored_to_a2() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["milestone"] == "V1.0.0-b1"
    assert contract["baseline"]["a2_merge_sha"] == ("eccb7f65a05707c2f7ea9a9881c930a641d65b92")


def test_plugin_discovery_is_deterministic_and_isolates_duplicate_job_ids() -> None:
    points = _EntryPoints(
        [
            _EntryPoint("z-later", "pkg.z:job", _SecondHealthy()),
            _EntryPoint("a-first", "pkg.a:job", _Healthy()),
        ]
    )
    with patch("pyingestkit.plugins.discovery.entry_points", return_value=points):
        report = discover_plugins()

    assert [job.id for job in report.jobs] == ["demo.same"]
    assert len(report.failures) == 1
    assert report.failures[0].entry_point == "z-later"
    assert "Duplicate ingestion job id 'demo.same'" in report.failures[0].error
    assert "a-first" in report.failures[0].error


def test_discover_jobs_is_strict_by_default_but_cli_helpers_can_be_tolerant() -> None:
    points = _EntryPoints(
        [
            _EntryPoint("healthy", "pkg.healthy:job", _Healthy()),
            _EntryPoint("broken", "pkg.broken:job", ImportError("missing dependency")),
        ]
    )
    with patch("pyingestkit.plugins.discovery.entry_points", return_value=points):
        with pytest.raises(PluginError, match="One or more ingestion plugins failed"):
            discover_jobs()
    with patch("pyingestkit.plugins.discovery.entry_points", return_value=points):
        assert [job.id for job in discover_jobs(strict=False)] == ["demo.same"]


def test_selected_config_profile_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYINGEST_CONFIG", raising=False)
    monkeypatch.setenv("PYINGEST_ENV", "prod")
    with pytest.raises(ConfigurationError, match="requires pyingest.yml.prod"):
        load_config()


def test_invalid_profile_name_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYINGEST_CONFIG", raising=False)
    monkeypatch.setenv("PYINGEST_ENV", "../../prod")
    with pytest.raises(ConfigurationError, match="simple profile name"):
        load_config()


def test_workspace_environment_overrides_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text("runtime:\n  workspace: from-yaml\n", encoding="utf-8")
    monkeypatch.setenv("PYINGEST_WORKSPACE", "from-env")
    assert load_config(config_path).runtime.workspace == Path("from-env")


def test_dotenv_templates_are_not_loaded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key = "PYINGESTKIT_B1_TEMPLATE_SENTINEL"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYINGEST_ENV", "dev")
    monkeypatch.delenv(key, raising=False)
    (tmp_path / "envs").mkdir()
    (tmp_path / "envs" / ".env.dev.example").write_text(f"{key}=unsafe-template\n")
    _load_local_dotenv()
    assert key not in __import__("os").environ


def test_root_dotenv_can_select_profile_and_profile_values_win(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    key = "PYINGESTKIT_B1_PROFILE_SENTINEL"
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYINGEST_ENV", raising=False)
    monkeypatch.delenv(key, raising=False)
    (tmp_path / "envs").mkdir()
    (tmp_path / ".env").write_text(f"PYINGEST_ENV=dev\n{key}=root\n", encoding="utf-8")
    (tmp_path / "envs" / ".env.dev").write_text(f"{key}=profile\n", encoding="utf-8")
    _load_local_dotenv()
    try:
        assert __import__("os").environ["PYINGEST_ENV"] == "dev"
        assert __import__("os").environ[key] == "profile"
    finally:
        __import__("os").environ.pop("PYINGEST_ENV", None)
        __import__("os").environ.pop(key, None)


def test_canonical_error_namespace_preserves_historical_identity() -> None:
    from pyingestkit.core.exceptions import PluginError as HistoricalPluginError
    from pyingestkit.sources.http import HttpError as HistoricalHttpError
    from pyingestkit.targets import TargetError as HistoricalTargetError

    assert errors.PluginError is HistoricalPluginError
    assert errors.HttpError is HistoricalHttpError
    assert errors.TargetError is HistoricalTargetError
    assert issubclass(errors.ReplayMismatchError, errors.ReplayError)
    assert issubclass(errors.ReplayError, errors.IngestionError)


def test_canonical_deprecation_warning_is_visible_by_default() -> None:
    with pytest.warns(PyIngestKitDeprecationWarning, match="old.flag is deprecated") as captured:
        warn_deprecated("old.flag", replacement="new.flag", removal="2.0.0")
    message = str(captured[0].message)
    assert "use new.flag instead" in message
    assert "removal in 2.0.0" in message


def test_file_logging_rejects_rich_format() -> None:
    with pytest.raises(PydanticValidationError, match="plain.*json"):
        FileLoggingConfig(format=LogOutputFormat.RICH)


def test_redaction_masks_url_credentials() -> None:
    redacted = redact_text("database=postgresql://alice:hunter2@db.example/app?token=secret-value")
    assert "hunter2" not in redacted
    assert "secret-value" not in redacted
    assert "alice:***REDACTED***@" in redacted


def test_json_exception_logging_redacts_credentials(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    configure_logging(
        PyIngestKitConfig().logging.model_copy(
            update={
                "console": False,
                "file": FileLoggingConfig(
                    enabled=True,
                    path=log_path,
                    level="INFO",
                    format=LogOutputFormat.JSON,
                ),
            }
        )
    )
    logger = logging.getLogger("pyingestkit.tests.b1")
    try:
        raise RuntimeError("postgresql://alice:hunter2@db/app token=secret-value")
    except RuntimeError:
        with log_context(run_id="12345678-aaaa-bbbb-cccc-123456789abc", job_id="demo.job"):
            logger.exception("execution failed")
    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["run_id"] == "12345678-aaaa-bbbb-cccc-123456789abc"
    assert "hunter2" not in payload["exception"]
    assert "secret-value" not in payload["exception"]


def test_cli_no_longer_exposes_accidental_completion_options() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--install-completion" not in result.output
    assert "--show-completion" not in result.output


def test_cli_exit_code_classes_are_stable() -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["--version"]).exit_code == 0
    assert runner.invoke(app, ["does-not-exist"]).exit_code == 2
    assert runner.invoke(app, ["inspect"]).exit_code == 2


def test_published_missing_pointer_is_controlled_domain_failure() -> None:
    class _NoPublicationStore:
        def get_published(self, dataset_id: str) -> None:
            del dataset_id
            return None

    runner = CliRunner()
    with (
        patch(
            "pyingestkit.cli.commands.published.project_config_or_exit",
            return_value=PyIngestKitConfig(),
        ),
        patch(
            "pyingestkit.cli.commands.published.dataset_version_store_or_exit",
            return_value=_NoPublicationStore(),
        ),
    ):
        result = runner.invoke(app, ["published", "demo.data"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "No published version found for dataset: demo.data" in result.output
