.PHONY: bootstrap install install-dev install-demo docs-install docs-build docs-serve docs-deploy test test-demo compatibility stability pilots rc stable check format quality security build wheel-smoke upgrade-smoke demo verify release-check clean

DOCS_VERSION ?= 1.0
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
	python -m pip install -e ".[docs]"

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

check: test test-demo compatibility stability pilots rc stable
	python -m compileall -q src tests examples/plugin_package/src examples/plugin_package/tests scripts

format:
	ruff check --fix src tests examples/plugin_package/src examples/plugin_package/tests
	ruff format src tests examples/plugin_package/src examples/plugin_package/tests

quality:
	ruff check src tests examples/plugin_package/src examples/plugin_package/tests
	ruff format --check src tests examples/plugin_package/src examples/plugin_package/tests
	mypy src/pyingestkit

security: bootstrap
	bandit -q -r src/pyingestkit examples/plugin_package/src
	pip-audit

build:
	python -m build
	python -m build examples/plugin_package

wheel-smoke:
	python scripts/wheel_smoke_test.py

upgrade-smoke:
	python scripts/upgrade_smoke_test.py

verify: check quality security build

release-check: verify wheel-smoke upgrade-smoke

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
