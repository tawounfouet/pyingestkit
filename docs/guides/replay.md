# Replay from historical RAW

Replay creates a **new ingestion run from historical RAW**. It is not an HTTP retry and it must not
silently reacquire the original live source.

## Replay the latest run

When no run ID is supplied, the CLI resolves the latest historical run visible through the active
metadata backend:

```bash
pyingest replay --config examples/plugin_package/demo-versioned.yml
```

Use this only when the active project/backend selection makes the intended source run unambiguous.

## Replay a specific run

```bash
pyingest replay <run-id> \
  --config examples/plugin_package/demo-versioned.yml
```

A full UUID or the CLI-supported historical selector may be used according to the active metadata
backend.

## Strict replay semantics

Framework HTTP and local sources resolve historical RAW through `ReplayContext`, verify the recorded
SHA-256 and materialize those bytes into the new run.

The invariant is:

```text
historical RAW exists and matches integrity metadata
  -> replay from historical bytes

historical RAW missing/corrupt/mismatched
  -> controlled replay failure
  -> NEVER fall back to live source acquisition
```

For runs with compatible DatasetVersion metadata, strict verification compares the replayed dataset
fingerprint with the expected historical fingerprint.

## Job-version changes

If the current job version differs from the historical run, the default strict compatibility path may
reject or downgrade verification according to the recorded context.

Use the explicit comparison mode only when the change is intentional:

```bash
pyingest replay <run-id> --allow-version-change
```

This is not permission to rewrite historical state. It records that replay is occurring across a job
version boundary.

## Disable fingerprint verification only deliberately

```bash
pyingest replay <run-id> --no-verify
```

`--no-verify` disables dataset fingerprint verification; it does not authorize live reacquisition and
does not disable RAW integrity checks that are required to materialize historical bytes safely.

Use it for investigation or explicitly governed migrations, not as the default operator path.

## Secrets are not historical replay inputs

Secret-looking runtime parameters are not restored from metadata. If downstream execution requires a
credential, provide it again through the current environment/configuration/provider chain.

Do not persist secrets merely to make replay convenient.

## Local vs remote durable RAW

With filesystem storage, historical replay depends on the retained workspace/artifact tree.

With `S3ArtifactStore`, the local parser cache can disappear. Replay resolves the durable
`storage_uri`, downloads/materializes the historical object into the current workspace and verifies
integrity before pipeline execution.

The B2 cross-host pilot proves this after destroying workspace A and replaying from a fresh workspace B
with PostgreSQL metadata plus S3-compatible durable storage.

## Inspect the replay result

After replay:

```bash
pyingest status --config examples/plugin_package/demo-versioned.yml
pyingest runs --config examples/plugin_package/demo-versioned.yml
```

For versioned datasets:

```bash
pyingest versions demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml
pyingest published demo.versioned_ndjson \
  --config examples/plugin_package/demo-versioned.yml
```

Replay is itself a new recorded run with lineage back to the source run.

## Older historical runs

Runs created before version/fingerprint metadata was available may be replayable only in best-effort
mode. The absence of newer metadata does not justify fabricating a strict verification result.

See:

- `docs/reference/compatibility-v1.md` for persisted compatibility;
- `docs/reference/pilots-v1.md` for the B2 replay evidence;
- `docs/guides/v1-production-pilot.md` for cross-host recovery.
