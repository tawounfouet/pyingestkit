# Quality reports

When `Runner` observes framework-owned validation/profile outputs it materializes portable JSON evidence under the run workspace:

```text
reports/validation.json
reports/profile.json
```

The manifest contains additive report references. `PROFILE_COMPLETED` and `QUALITY_REPORT_WRITTEN` events make profiling/report generation observable without a new SQL schema. `pyingest status` includes report references in human and JSON output.
