# Quickstart

This quickstart uses the maintained demo plugin so you can exercise the framework without writing a connector first.

## 1. Prepare a checkout

```bash
git clone https://github.com/tawounfouet/pyingestkit.git
cd pyingestkit
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,excel,parquet,postgres,s3]"
python -m pip install -e examples/plugin_package
```

## 2. Inspect the available jobs

```bash
pyingest --version
pyingest config
pyingest jobs
pyingest inspect demo.local_file
```

## 3. Run the first ingestion

```bash
pyingest run demo.local_file \
  --config examples/plugin_package/demo.yml
```

Then inspect the execution history:

```bash
pyingest runs
pyingest status
```

## 4. Exercise HTTP and quality flows

```bash
pyingest run demo.http_csv --config examples/plugin_package/demo-http.yml
pyingest run demo.http_json --config examples/plugin_package/demo-http.yml
pyingest run demo.ndjson_quality --config examples/plugin_package/demo-quality.yml
```

## 5. Exercise versioning and replay

```bash
pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=1

pyingest run demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml \
  --param revision=2

pyingest versions demo.versioned_ndjson
pyingest published demo.versioned_ndjson
pyingest replay
```

For a complete operator journey, continue with the [V1 quickstart](../guides/v1-quickstart.md). For the production-like PostgreSQL + S3 topology, see the [V1 production pilot](../guides/v1-production-pilot.md).
