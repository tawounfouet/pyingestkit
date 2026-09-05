# V1.0.0 stable release validation

This guide defines the release-blocking qualification for **PyIngestKit 1.0.0**.

The stable milestone is a promotion of the qualified RC1 contract. It must not introduce a new provider,
orchestration platform or persisted-schema version.

## Stable identity

Expected framework version:

```text
1.0.0
```

Expected maintained demo package version:

```text
1.0.0
```

Expected demo dependency range:

```text
pyingestkit>=1.0.0,<1.1
```

Expected distributions:

```text
pyingestkit-1.0.0-py3-none-any.whl
pyingestkit-1.0.0.tar.gz
pyingestkit_demo_jobs-1.0.0-py3-none-any.whl
pyingestkit_demo_jobs-1.0.0.tar.gz
SHA256SUMS
```

## Release lineage

The stable branch starts from the post-merge-qualified RC1 baseline:

```text
e98a12cc3bbfb634d2fd2257f43049fa1e0333dd
```

The historical upgrade baseline remains immutable `v0.6.0`.

## Local qualification

From a clone with full history and the `v0.6.0` tag:

```bash
make release-check
```

The release-check is cumulative:

```text
unit + contract + integration tests
        ↓
A1 public API inventory
        ↓
A2 compatibility / persisted logical contract
        ↓
B1 operational stability
        ↓
B2 representative pilots + docs
        ↓
historical RC1 evidence integrity
        ↓
V1.0.0 stable release contract
        ↓
Ruff + formatting + Mypy
        ↓
Bandit + pip-audit
        ↓
wheel + sdist build
        ↓
clean install from 1.0.0 wheels
        ↓
real V0.6.0 -> 1.0.0 upgrade + strict replay
```

## CI qualification

The stable branch, stable PR head and exact merge SHA must pass:

```text
test (Python 3.11)
test (Python 3.12)
test (Python 3.13)
postgres-e2e
s3-e2e
object-storage-e2e
foundation-verify
v1-pilot-gate
v1-rc-history-gate
stable-release-gate
Security / audit
```

`foundation-verify` checks out full history and tags because the upgrade smoke consumes the immutable
`v0.6.0` release.

## CI artifacts

Stable CI evidence is named:

```text
pyingestkit-v1.0.0-source
pyingestkit-v1.0.0-dist
```

The distribution artifact contains framework wheel/sdist, demo wheel/sdist and `SHA256SUMS`.
RC1 artifacts remain historical candidate evidence and are never renamed into stable distributions.

## Tag gate

Do **not** create `v1.0.0` on the release branch or PR head.

The required sequence is:

```text
qualified stable branch head
        ↓
PR CI + Security green
        ↓
merge commit to protected main
        ↓
post-merge CI + Security green on exact merge SHA
        ↓
annotated v1.0.0 tag on that exact SHA
        ↓
verify tag dereference
        ↓
publish GitHub release + final distributions + SHA256SUMS
```

The tag is immutable after publication. It must never be moved to a later commit.

## Tag verification

After the post-merge gate passes:

```bash
git fetch --tags origin
git rev-parse v1.0.0^{}
git rev-parse origin/main
```

Both SHAs must be the exact qualified stable merge SHA at release time.

## Release asset verification

Before publication, verify the checksum manifest against the exact artifacts produced from the stable
lineage. The release must include framework/demo wheel and sdist plus `SHA256SUMS`; a source archive may
also be attached as release evidence.

## Immutable historical evidence

Never move or redefine `v0.6.0` or the future `v1.0.0` tag. Never rewrite milestone history merely to
clean historical scanner annotations. Release SHAs, checksums and tags are part of the qualification
evidence.
