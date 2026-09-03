.PHONY: test check

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

check: test
	python scripts/check_zero_runtime_dependencies.py
	python scripts/check_public_api.py
