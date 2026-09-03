# V0.2.0 release validation

PyIngestKit V0.2.0 uses two complementary release gates.

## Source gate

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install -e examples/plugin_package
make verify
```

This validates tests, public API, compilation, Ruff, Mypy, Bandit, pip-audit, and both distribution builds.

## Distribution gate

The final wheels must then be installed into a fresh virtual environment, without editable installs or `PYTHONPATH`, and the installed CLI must execute:

```text
pyingest --version
pyingest jobs
pyingest run demo.local_file
pyingest run demo.http_csv
pyingest run demo.http_json
```

The HTTP demo configuration uses the deterministic fixture transport. HTTP test suites additionally block socket connections, so acquisition E2E tests are independent of external network availability.

## Release artifacts

The release produces a clean source ZIP, framework wheel/sdist, demo-job wheel/sdist, and a validation-evidence ZIP containing reproducible command outputs and SHA-256 checksums. Generated build outputs are deliberately absent from the source ZIP.
