.PHONY: bootstrap install install-dev install-demo docs-install docs-build docs-serve docs-deploy test test-v2 test-demo compatibility stability pilots rc stable check check-v2 format quality security build wheel-smoke upgrade-smoke demo verify release-check stable-v2 compatibility-v2 milestone-v2 architecture-v2 contract-v2 v2-core v2-baseline clean

DOCS_VERSION ?= 2.0
DOCS_ALIAS ?= latest

bootstrap:
	python -m pip install --upgrade pip

install:
	python -m pip install -e .

install-dev: bootstrap
	python -m pip install -e ".[dev]"

install-demo:
	python -m pip install -e examples/plugin_package

docs-install: bootstrap
	python -m pip install -e .
	python -m pip install -r docs/requirements.txt

docs-build:
	mkdocs build --strict

docs-serve:
	mkdocs serve

docs-deploy:
	mike deploy --push --update-aliases $(DOCS_VERSION) $(DOCS_ALIAS)
	mike set-default --push $(DOCS_ALIAS)

test:
	PYTHONPATH=src:examples/plugin_package/src python -m unittest discover -s tests -v
	PYTHONPATH=src:examples/plugin_package/src pytest

test-v2:
	PYTHONPATH=src pytest -q tests/architecture tests/contract/public_api tests/unit/v2 tests/conformance/v2 tests/integration/v2 tests/migration/v2

test-demo:
	PYTHONPATH=src:examples/plugin_package/src python -m unittest discover -s examples/plugin_package/tests -v

compatibility:
	PYTHONPATH=src python scripts/check_public_api.py
	PYTHONPATH=src python scripts/check_v1_compatibility.py

stability:
	PYTHONPATH=src python scripts/check_v1_stability.py

pilots:
	PYTHONPATH=src python scripts/check_v1_pilots.py

rc:
	PYTHONPATH=src python scripts/check_v1_rc.py

stable:
	PYTHONPATH=src python scripts/check_v1_stable.py

architecture-v2:
	PYTHONPATH=src pytest -q tests/architecture

contract-v2:
	PYTHONPATH=src pytest -q tests/contract/public_api

v2-core:
	PYTHONPATH=src pytest -q tests/unit/v2 tests/conformance/v2 tests/contract/public_api

v2-baseline: architecture-v2 contract-v2 v2-core
	python -m compileall -q src/pyingestkit tests/architecture tests/contract/public_api tests/unit/v2 tests/conformance/v2

check-v2: test-v2 v2-baseline
	python -m compileall -q src/pyingestkit tests/architecture tests/contract/public_api tests/unit/v2 tests/conformance/v2 tests/integration/v2 tests/migration/v2 scripts

check: check-v2

format:
	ruff check --fix src tests examples/plugin_package/src examples/plugin_package/tests
	ruff format src tests examples/plugin_package/src examples/plugin_package/tests

quality:
	ruff check src/pyingestkit tests/architecture tests/contract/public_api tests/unit/v2 tests/conformance/v2 tests/integration/v2 tests/migration/v2 scripts/check_v2*.py
	ruff format --check src/pyingestkit tests/architecture tests/contract/public_api tests/unit/v2 tests/conformance/v2 tests/integration/v2 tests/migration/v2 scripts/check_v2*.py
	mypy src/pyingestkit/__init__.py src/pyingestkit/_api_v2.py src/pyingestkit/_architecture_v2.py src/pyingestkit/domain src/pyingestkit/application src/pyingestkit/ports src/pyingestkit/governance src/pyingestkit/adapters/memory src/pyingestkit/adapters/filesystem src/pyingestkit/adapters/formats src/pyingestkit/adapters/http src/pyingestkit/adapters/postgres src/pyingestkit/adapters/s3 src/pyingestkit/serialization src/pyingestkit/integrations src/pyingestkit/migration

security: bootstrap
	bandit -q -r src/pyingestkit
	pip-audit

build:
	python -m build

wheel-smoke:
	python scripts/wheel_smoke_test.py

upgrade-smoke:
	python scripts/upgrade_smoke_test.py

verify: check-v2 quality security build

compatibility-v2:
	PYTHONPATH=src python scripts/check_v2_compatibility.py

milestone-v2:
	PYTHONPATH=src python scripts/check_v2_1_beta2.py

stable-v2: compatibility-v2

release-check: verify compatibility-v2 milestone-v2

demo: install-demo
	pyingest jobs
	pyingest inspect demo.local_file
	pyingest inspect demo.http_csv
	pyingest inspect demo.http_json
	pyingest run demo.local_file --config examples/plugin_package/demo.yml
	pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
	pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
	pyingest runs

clean:
	rm -rf .pyingest build dist site *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find src examples -type d -name '*.egg-info' -prune -exec rm -rf {} +
