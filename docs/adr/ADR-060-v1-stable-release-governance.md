# ADR-060 — V1.0.0 stable is a promotion of the qualified RC1 contract

Status: Accepted for **V1.0.0 stable**.

## Context

The exact RC1 merge SHA `e98a12cc3bbfb634d2fd2257f43049fa1e0333dd` passed post-merge CI and
Security. RC1 already proved the governed Python/CLI/config/plugin/observability contracts, persistence
compatibility, representative pilots, clean-wheel installation and a real V0.6.0 -> V1 package
upgrade with strict replay.

The stable milestone must therefore publish the qualified contract, not use the version transition as
an opportunity to add product scope.

## Decision

### 1. Stable package identity is 1.0.0

The framework and maintained demo distribution are both built as `1.0.0`. The demo package depends on
`pyingestkit>=1.0.0,<1.1`.

### 2. RC1 is the stable baseline

Stable V1 is anchored to RC1 merge SHA `e98a12cc3bbfb634d2fd2257f43049fa1e0333dd`. The historical RC1
contract and release notes remain in the repository as evidence; they are not rewritten to pretend RC1
was stable.

### 3. Stable candidates are promoted, experimentals are not

The A1 public API inventory is historical evidence and keeps its `PUBLIC_STABLE_CANDIDATE`
classification vocabulary. At `1.0.0`, every such governed candidate that survived A2, B1, B2 and RC1
qualification is promoted to the stable 1.x compatibility contract. Explicitly experimental modules or
symbols remain experimental.

The effective stable policy is recorded separately in
`tests/contract/fixtures/stable_release_v1.json` and `docs/reference/stable-contract-v1.md`.

### 4. Stable adds no product or persisted-schema scope

The stable promotion introduces no new provider, orchestration platform or persistent schema version.
It changes release identity, documentation and release governance only.

### 5. Full qualification is repeated on stable wheels

The stable branch must rerun the entire release stack: Python 3.11/3.12/3.13, PostgreSQL, S3-compatible
object storage, cross-host replay, A1/A2/B1/B2 contracts, stable release contract, Ruff/Mypy,
Bandit/pip-audit, wheel/sdist build, clean-wheel install and the real V0.6.0 -> 1.0.0 upgrade smoke.

### 6. The stable tag is post-merge evidence

The tag `v1.0.0` is created only after:

1. the stable branch head is qualified;
2. its PR passes CI and Security;
3. the PR is merged with a merge commit;
4. the exact merge SHA passes post-merge CI and Security.

The tag is annotated, points exactly to that qualified merge SHA, and is immutable once pushed.

### 7. Release assets are derived from the qualified stable SHA

Final framework/demo wheels and sdists plus `SHA256SUMS` are published from the qualified stable
lineage. Candidate artifacts are not renamed and reused as stable binaries.

### 8. V0.6.0 remains immutable upgrade evidence

The existing `v0.6.0` tag remains unchanged. Stable release qualification repeats the executable
upgrade from that exact historical tag and requires historical run/version/publication readability plus
strict replay fingerprint equality.

## Consequences

- `1.0.0` establishes the first protected 1.x compatibility line.
- Stable public surfaces now require deprecation/migration discipline throughout 1.x.
- Explicit experimental surfaces may still evolve without being misrepresented as stable.
- Release tags become evidence pointers, not movable labels.
- Any later 1.x release must preserve the stable contract or use the documented deprecation policy.
