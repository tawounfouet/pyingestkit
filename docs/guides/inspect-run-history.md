# Inspect run history

```bash
pyingest runs
pyingest runs --job demo.local_file --status FAILED
pyingest status <full-uuid-or-unique-prefix>
```

Both commands support `--json` and read only through the MetadataStore abstraction.
