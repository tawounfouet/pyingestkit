# Dataset Contracts V2

Quality Contracts V2 extend the V0.2 `FieldContract` / `DatasetContract` surface without changing its core rule: **validation reports; it does not normalize**.

```python
from pyingestkit.contracts import DatasetContract, FieldContract

contract = DatasetContract(
    fields=(
        FieldContract(
            "postal_code",
            nullable=False,
            expected_type=str,
            pattern=r"[0-9]{5}",
            min_length=5,
            max_length=5,
        ),
        FieldContract(
            "status",
            expected_type=str,
            allowed_values=("ACTIVE", "INACTIVE"),
        ),
    ),
    unique_together=(("postal_code", "status"),),
    primary_key=("postal_code",),
    max_issues=100,
)
```

## Field rules

- `field.allowed_values`
- `field.pattern` (`re.fullmatch` semantics)
- `field.min_value` / `field.max_value`
- `field.min_length` / `field.max_length`

Existing V0.2 rules such as `field.required`, `field.null`, `field.type`, and `field.unique` remain stable.

## Dataset rules

`unique_together` validates exact composite uniqueness. `primary_key` is a logical dataset identity constraint: every key field must be present, every key value must be non-null, and composite key values must be unique. It does not create SQL schema.

## Bounded issues

`max_issues` limits detailed issue objects. Once the limit is reached the result exposes `issues_truncated=True`. Counts reflect the returned bounded issue stream; PyIngestKit does not pretend it counted unseen violations after deterministic truncation.

## Safe previews

V2 issues can include a bounded `value_preview`, `constraint`, and compact `context`. Values from fields whose names look secret (`password`, `token`, `api_key`, etc.) are replaced with `<redacted>`. Complete rows are never copied into issue payloads.
