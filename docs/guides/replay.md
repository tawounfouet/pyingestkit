# Replay from historical RAW

```bash
pyingest replay <run-id>
pyingest replay <run-id> --allow-version-change
pyingest replay <run-id> --no-verify
```

Replay is a new run, not an HTTP retry. Framework HTTP and local sources resolve historical RAW through `ReplayContext`, verify the recorded SHA-256, copy the bytes into the new run, and never fall back to the live source. Secret-looking parameters are not restored from metadata; provide required downstream secrets explicitly through config/env/`--param`.

Same job version + known DatasetVersion enables strict fingerprint verification. Old runs without V0.4 version metadata are replayed best-effort.
