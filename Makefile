.PHONY: install install-dev install-demo test test-demo check quality security build demo

install:
	python -m pip install -e .

install-dev:
	python -m pip install -e ".[dev]"

install-demo:
	python -m pip install -e examples/plugin_package

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

test-demo:
	PYTHONPATH=examples/plugin_package/src python -m unittest discover -s examples/plugin_package/tests -v

check: test test-demo
	PYTHONPATH=src python scripts/check_public_api.py
	python -m compileall -q src tests examples/plugin_package/src examples/plugin_package/tests

quality:
	ruff check src tests examples/plugin_package/src examples/plugin_package/tests
	mypy src/pyingestkit

security:
	bandit -q -r src/pyingestkit examples/plugin_package/src
	pip-audit

build: check
	python -m build

demo: install-demo
	pyingest jobs
	pyingest inspect demo.local_file
	pyingest run demo.local_file --config examples/plugin_package/demo.yml
