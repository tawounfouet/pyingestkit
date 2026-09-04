# Dataset Contracts V2

PyIngestKit V0.3.0-a1 extends structural dataset validation without adding business
normalization or dataframe dependencies.

```python
from pyingestkit import DatasetContract, FieldContract

contract = DatasetContract(
    fields=(
        FieldContract(
            "postal_code",
            nullable=False,
            expected_type=str,
            pattern=r"^\d{5}$",
            min_length=5,
            max_length=5,
        ),
        FieldContract("country", allowed_values={"FR", "BE", "CH"}),
        FieldContract("score", expected_type=int, min_value=0, max_value=100),
    ),
    unique_together=(("country", "postal_code"),),
    primary_key=("country", "postal_code"),
    max_issues=1000,
)
```

## Guardrails

- `validate()` never mutates a `Dataset`.
- `"42"` is not converted to `42`.
- regex matching uses `re.fullmatch`.
- `min_length` / `max_length` are string constraints in Alpha 1.
- `primary_key` is a logical dataset key, not SQL DDL.
- issue previews are bounded and secret-looking field names are redacted.
