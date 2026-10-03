# PyIngestKit V2 — LOT-12 Runtime Surface Cutover

LOT-12 closes the transitional ambiguity between the stable V1 runtime and the
new V2 execution model.

The repository keeps the V1 surface for maintenance compatibility:

```python
from pyingestkit.runtime import Runner
```

but V2 code has exactly one runtime-facing surface:

```python
from pyingestkit.runtime.v2 import IngestionRun, IngestionResult, IngestionRuntime
```

## Cutover invariant

```text
V1 maintenance callers
        |
        +--> pyingestkit.runtime.__init__ -> Runner

V2 callers / V2 modules
        |
        +--> pyingestkit.runtime.v2
                |
                +--> IngestionRun
                +--> IngestionResult
                +--> IngestionRuntime
```

New V2 code must not import:

- `pyingestkit.runtime.runner`;
- `Runner`;
- `pyingestkit.core` execution values;
- V1 Job/Pipeline/Step runtime semantics.

The qualified V2 surface may delegate implementation to the application/domain
layers, but it must remain provider-neutral.

## Why V1 is not removed

LOT-12 is a V2 cutover, not the 2.0 package-root breaking change. The maintained
V1 contract therefore remains:

```python
pyingestkit.runtime.__all__ == ["Runner"]
```

The eventual 2.0 alpha package cut can promote the qualified V2 symbols without
forcing an early breaking change during migration.

## Provider boundary

LOT-12 also closes the temporary architecture note that reserved runtime
provider neutrality for a future lot. The rule is now permanent:

```text
domain       -> no providers
application  -> ports, never provider SDKs/adapters
runtime.v2   -> application/domain surface only
ports        -> no adapters/runtime
adapters     -> provider-specific implementation
```

HTTP, PostgreSQL and S3 remain adapter lots (LOT-13, LOT-14 and LOT-15).

## Acceptance

LOT-12 is accepted when:

- the V1 runtime export surface is byte-for-byte unchanged;
- the V2 runtime qualified export set is explicit and contract-tested;
- V2-owned layers contain no import of `runtime.runner`;
- V2-owned layers contain no import of legacy `pyingestkit.core` execution;
- the provider-neutral application rule is permanent rather than transitional;
- the full V1 compatibility gates remain green.
