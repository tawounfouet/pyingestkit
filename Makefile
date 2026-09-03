.PHONY: test check quality security build

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

check: test
	PYTHONPATH=src python scripts/check_public_api.py
	python -m compileall -q src tests

quality:
	ruff check src tests
	mypy src/pyingestkit

security:
	bandit -q -r src/pyingestkit
	pip-audit

build: check
	python -m build
