# PyIngestKit V0.3.0 — Quality & Formats

## Architecture & implementation plan

**Status:** implementation plan  
**Baseline:** PyIngestKit V0.2.0 — Acquisition Release  
**Target:** V0.3.0 — Quality & Formats  
**Date:** 2026-09-04

---

# 1. Executive summary

PyIngestKit V0.2.0 established the first complete acquisition vertical slice:

```text
HTTP / local source
        ↓
RAW immutable bytes
        ↓
SHA-256 + provenance
        ↓
CSV / JSON Parser
        ↓
Dataset
        ↓
DatasetContract
        ↓
ValidationResult
        ↓
Manifest + Metadata + Events
```

V0.3.0 extends this foundation in two dimensions:

```text
QUALITY
   ↓
Contracts V2
Profiling
Quality Reports

FORMATS
   ↓
NDJSON
Excel
Parquet
```

The goal is not to build a data-processing engine. The goal is to make structured ingestion substantially safer and more useful while retaining a small, dependency-neutral framework contract.

The target V0.3 architecture is:

```text
RawArtifact
     │
     ▼
   Parser
 ┌───┼───────────────┐
 ▼   ▼               ▼
CSV JSON          NDJSON
                  Excel
                  Parquet
     │
     ▼
  Dataset
     │
 ┌───┴───────────────┐
 ▼                   ▼
DatasetContract V2   DatasetProfiler
 │                   │
 ▼                   ▼
ValidationResult     DatasetProfile
 │                   │
 └──────────┬────────┘
            ▼
       Quality Reports
            │
            ▼
 Manifest / Metadata / Events
```

---

# 2. Product boundary

PyIngestKit continues to own:

> **HOW TO INGEST**

External systems continue to own:

> **WHEN TO RUN**

V0.3 therefore remains an ingestion framework, not an orchestration platform.

The following remain explicitly outside the V0.3 boundary:

- DAG scheduling;
- distributed execution;
- workers;
- task queues;
- cluster management;
- data catalog;
- IAM;
- secrets vault;
- business workflow engine;
- data warehouse transformation framework;
- BI/reporting system;
- AI/RAG pipeline;
- ML anomaly-detection platform.

---

# 3. Baseline inherited from V0.2.0

V0.3 MUST preserve the public contracts released by V0.2.0 unless a documented compatibility reason requires otherwise.

The inherited stable surfaces include:

```text
pyingestkit.Dataset

pyingestkit.parsers.Parser
pyingestkit.parsers.CsvParser
pyingestkit.parsers.JsonParser

pyingestkit.contracts.FieldContract
pyingestkit.contracts.DatasetContract

pyingestkit.validation.ValidationIssue
pyingestkit.validation.ValidationResult
pyingestkit.validation.ValidationSeverity

pyingestkit.sources.http.*
pyingestkit.retry.*

RawArtifact
ArtifactStore
MetadataStore
RunManifest
Runner
```

The V0.3 rule is:

```text
V0.2 public API
       │
       ├── remains valid
       │
       └── gains additive capabilities
```

---

# 4. V0.3 objectives

V0.3 has six principal objectives.

## 4.1 Contracts V2

Increase the expressiveness of structural dataset validation without creating a general-purpose validation language.

## 4.2 Profiling

Provide deterministic, lightweight descriptive statistics for ingestion triage and observability.

## 4.3 Quality Reports

Create portable machine-readable evidence from validation and profiling.

## 4.4 NDJSON

Support line-delimited JSON as a common ingestion serialization.

## 4.5 Excel

Support real operational spreadsheet ingestion without making spreadsheet tooling a mandatory dependency.

## 4.6 Parquet

Support columnar ingestion through an optional mature Arrow backend while preserving the framework's neutral Dataset boundary.

---

# 5. Non-objectives

V0.3 will NOT introduce:

```text
pandas as mandatory dependency
polars as mandatory dependency
pyarrow as mandatory dependency
Spark
DuckDB as framework runtime engine
Great Expectations-style DSL
Pandera-style dataframe binding
SQL transformation engine
schema registry service
semantic type inference platform
ML anomaly detection
streaming engine
async Runner
multiprocessing framework
```

This is important because several of these technologies may be useful **with** PyIngestKit without belonging **inside** PyIngestKit.

---

# 6. Core quality philosophy

The V0.3 quality model is based on four separations:

```text
PARSE
  ≠
NORMALIZE

VALIDATE
  ≠
TRANSFORM

PROFILE
  ≠
INFER BUSINESS MEANING

REPORT
  ≠
CATALOG
```

A framework primitive should describe what it observes or whether a declared rule passes. It should not silently rewrite the dataset.

---

# 7. Dataset Contracts V2

## 7.1 Existing V0.2 contract

V0.2 supports roughly:

```python
FieldContract(
    name="id",
    required=True,
    nullable=False,
    expected_type=int,
    unique=True,
)
```

and:

```python
DatasetContract(
    fields=(...),
    allow_extra_fields=False,
    min_rows=1,
    max_rows=None,
)
```

This is a suitable foundation but insufficient for many reference-data ingestion jobs.

---

# 8. FieldContract V2

Proposed V0.3 surface:

```python
FieldContract(
    name="code",

    required=True,
    nullable=False,

    expected_type=str,
    unique=True,

    allowed_values=None,
    regex=None,

    min_value=None,
    max_value=None,

    min_length=None,
    max_length=None,
)
```

Conceptually:

```text
FieldContract
├── existence
├── nullability
├── runtime type
├── uniqueness
├── membership
├── pattern
├── numeric/comparable range
└── length
```

---

# 9. `allowed_values`

Example:

```python
FieldContract(
    name="status",
    expected_type=str,
    allowed_values=("ACTIVE", "INACTIVE"),
)
```

Issue:

```text
field.allowed_values
```

Expected behavior:

```text
ACTIVE      → valid
INACTIVE    → valid
UNKNOWN     → ERROR
None        → governed by nullable
```

The contract MUST NOT normalize:

```text
"active"
   ↓
"ACTIVE"
```

That belongs to a normalizer.

---

# 10. Regex constraint

Example:

```python
FieldContract(
    name="postal_code",
    expected_type=str,
    regex=r"^[0-9]{5}$",
)
```

Issue:

```text
field.regex
```

The regular expression is applied only when the value is compatible with string matching.

A mismatched type should first produce:

```text
field.type
```

rather than an opaque regex exception.

---

# 11. Numeric/comparable range

Example:

```python
FieldContract(
    name="population",
    expected_type=int,
    min_value=0,
)
```

Possible rules:

```text
field.min_value
field.max_value
```

Comparison failures caused by incompatible values must become validation issues or be skipped after a type failure; they must not crash the validator.

---

# 12. Length constraints

Example:

```python
FieldContract(
    name="code",
    expected_type=str,
    min_length=2,
    max_length=10,
)
```

Rules:

```text
field.min_length
field.max_length
```

For V0.3 these constraints should target string-like values rather than attempting to define universal collection semantics.

---

# 13. DatasetContract V2

Proposed conceptual surface:

```python
DatasetContract(
    fields=(...),

    allow_extra_fields=True,

    min_rows=None,
    max_rows=None,

    unique_fields=(),
    composite_unique=(),
    primary_key=(),

    issue_limit=None,
)
```

Naming should remain concise and Pythonic. Exact constructor names are frozen during Alpha 1 implementation.

---

# 14. Composite uniqueness

A common ingestion requirement is:

```text
(country_code, postal_code)
```

must be unique as a pair.

Example conceptual contract:

```python
DatasetContract(
    composite_unique=(
        ("country_code", "postal_code"),
    ),
)
```

Rule:

```text
dataset.composite_unique
```

The error should reference:

- row index;
- involved field names;
- first duplicate row where practical;
- never the full row payload.

---

# 15. Primary key semantics

`primary_key` in PyIngestKit V0.3 means:

```text
logical dataset identity constraint
```

It does NOT mean:

```text
SQL PRIMARY KEY creation
```

A primary key requires:

```text
all fields present
AND
all values non-null
AND
composite values unique
```

This is validation semantics only.

---

# 16. Issue limit

A malformed public dataset could contain millions of violations.

Returning millions of Python `ValidationIssue` objects is undesirable.

The contract should support:

```text
issue_limit
```

Example:

```python
DatasetContract(
    issue_limit=1_000,
)
```

The validation result should record that output was truncated.

Example conceptual result:

```text
is_valid            false
error_count          >=1000
issues_returned      1000
issues_truncated     true
```

The implementation must define carefully whether counts are exact or bounded.

For V0.3-a1, the recommended implementation is:

```text
stop collecting detailed issues after limit
continue only if needed for deterministic aggregate counts
```

If exact aggregate counting creates excessive complexity, document the bounded semantics explicitly rather than hiding them.

---

# 17. ValidationIssue V2

Existing V0.2 issue:

```text
rule
message
severity
field
row_index
```

V0.3 may enrich this carefully:

```text
rule
message
severity
field
row_index
value_preview
constraint
context
```

The important security boundary is:

```text
value_preview ≠ raw record dump
```

A validation issue must not become a secret leakage mechanism.

Recommended preview policy:

```text
strings       → bounded length
bytes         → never raw full bytes
collections   → type + size / bounded representation
secret fields → redacted when identifiable
```

---

# 18. Severity model

Retain:

```text
ERROR
WARNING
REVIEW
```

Semantics:

```text
ERROR
  → contract invalid
  → Runner may fail producing step/run

WARNING
  → observable
  → non-blocking

REVIEW
  → observable
  → non-blocking
```

V0.3 does not need a configurable severity expression language.

---

# 19. Validation remains pure

Core rule:

```python
before = dataset
result = contract.validate(dataset)
after = dataset

assert before == after
```

Conceptually:

```text
Dataset
   │
   ▼
Contract
   │
   ├── ValidationResult
   │
   └── Dataset unchanged
```

---

# 20. Dataset profiling

V0.3 introduces lightweight profiling.

Proposed API:

```python
profile = dataset.profile()
```

or:

```python
profile = DatasetProfiler().profile(dataset)
```

The second form provides a cleaner separation of concerns and should be preferred internally even if a convenience method exists later.

---

# 21. DatasetProfile

Conceptual model:

```python
DatasetProfile(
    row_count=1000,
    column_count=8,
    duplicate_count=3,
    fields={...},
)
```

Field profile:

```python
FieldProfile(
    name="population",
    null_count=3,
    distinct_count=997,
    observed_types=("int",),
    min_value=12,
    max_value=2_300_000,
)
```

---

# 22. Required profile metrics

Dataset-level:

```text
row_count
column_count
duplicate_count
```

Field-level:

```text
null_count
non_null_count
distinct_count
observed_types
```

Where safe/applicable:

```text
min
max
min_length
max_length
```

---

# 23. Type profiling

The profiler must remain modest.

It may report:

```text
str
int
float
bool
NoneType
datetime
date
list
dict
```

It should NOT attempt semantic guessing such as:

```text
email
telephone
SIRET
postal code
ISO country
IBAN
```

Those are semantic/domain concerns.

---

# 24. Duplicate counting

A duplicate row means exact structural equality across dataset fields.

Potential issue:

```python
{"metadata": {"a": 1}}
```

contains an unhashable dict.

The profiler therefore needs a stable structural representation for duplicate detection.

Example internal canonicalization:

```text
scalar → scalar
list   → tuple(recursive)
dict   → sorted tuple(key, canonical(value))
```

This helper should be private and deterministic.

---

# 25. Profiling and memory

Current Dataset materializes all rows.

Therefore V0.3 profiling is allowed to be exact and materialized.

However, API semantics should not make future streaming impossible.

Avoid promises like:

```python
profile.internal_dataframe
profile.numpy_array
```

Prefer pure immutable values.

---

# 26. Profile immutability

Profile objects should be:

```python
@dataclass(frozen=True, slots=True)
```

or equivalent immutable Pydantic/data structure where justified.

They represent evidence, not mutable processing state.

---

# 27. Profiling must be deterministic

Given the same Dataset:

```text
profile(dataset)
```

must produce the same logical result.

Do not include unstable values such as:

```text
memory addresses
random sample order
process ID
hash-randomized output
```

Timing metadata may be stored separately from logical profile content if required.

---

# 28. Quality reports

V0.3 should formalize run reports.

Current workspace already contains:

```text
runs/<namespace>/<job>/<run-id>/reports/
```

V0.3 uses that explicitly.

---

# 29. Validation report artifact

Target:

```text
reports/validation.json
```

Example structure:

```json
{
  "schema_version": 1,
  "kind": "validation",
  "contract_id": "postal_codes.v1",
  "dataset": {
    "rows": 35892,
    "fields": 12
  },
  "status": "PASSED",
  "summary": {
    "errors": 0,
    "warnings": 2,
    "review": 0
  },
  "issues": []
}
```

The exact schema must be stable and documented before stable V0.3.

---

# 30. Profile report artifact

Target:

```text
reports/profile.json
```

Example:

```json
{
  "schema_version": 1,
  "kind": "profile",
  "dataset": {
    "row_count": 35892,
    "column_count": 12,
    "duplicate_count": 0
  },
  "fields": {
    "postal_code": {
      "null_count": 0,
      "distinct_count": 6329,
      "observed_types": ["str"]
    }
  }
}
```

---

# 31. Report ownership

Reports are produced by framework quality primitives.

They must be linked to:

```text
run_id
job_id
step
source artifact where available
```

This allows later correlation:

```text
RAW
 ↓
Dataset
 ↓
Validation/Profile
 ↓
Report
```

---

# 32. Manifest integration

`manifest.json` should not duplicate the complete report unnecessarily.

Prefer:

```json
{
  "reports": [
    {
      "kind": "validation",
      "path": "reports/validation.json"
    },
    {
      "kind": "profile",
      "path": "reports/profile.json"
    }
  ]
}
```

Manifest:

```text
index / summary
```

Report:

```text
detailed evidence
```

---

# 33. Metadata integration

V0.2 already persists validation records.

V0.3 should avoid duplicating an entire profile in relational metadata.

Recommended strategy:

```text
MetadataStore
    │
    ├── validation summaries
    │
    └── report artifact references
```

If the current metadata schema cannot store generic report references cleanly, use artifact metadata rather than adding specialized `profiles` tables prematurely.

---

# 34. Events

Potential runtime events:

```text
VALIDATION_COMPLETED     existing
PROFILE_COMPLETED        new
QUALITY_REPORT_WRITTEN   new
```

Payloads should be summaries only.

Example:

```json
{
  "row_count": 12000,
  "error_count": 0,
  "report": "reports/validation.json"
}
```

Do not place entire issue lists into event payloads.

---

# 35. NDJSON

NDJSON is the first new parser format because it is operationally common and introduces little dependency cost.

Format:

```text
{"id":1,"name":"A"}
{"id":2,"name":"B"}
{"id":3,"name":"C"}
```

---

# 36. NdjsonParser

Proposed:

```python
NdjsonParser(
    encoding="utf-8",
    skip_blank_lines=True,
)
```

Behavior:

```text
RawArtifact
    ↓
decode text
    ↓
line iteration
    ↓
json.loads(line)
    ↓
object validation
    ↓
Dataset
```

Each non-empty line must decode to an object/mapping.

---

# 37. NDJSON error model

Malformed line:

```text
line 153 is invalid JSON
```

Should become:

```text
ParseError
```

with safe context:

```text
line_number=153
```

Avoid embedding the entire source line if it may contain sensitive data.

---

# 38. NDJSON type semantics

As with JsonParser:

```text
JSON string  → str
JSON number  → int/float
JSON boolean → bool
JSON null    → None
JSON object  → dict
JSON array   → list
```

No business coercion.

---

# 39. NDJSON memory boundary

Initial V0.3 implementation may materialize all rows because Dataset itself is materialized.

However the parser implementation should preferably process lines incrementally before constructing the final Dataset rather than first building a second complete parsed JSON document.

This reduces unnecessary intermediate memory usage and aligns with future streaming work.

---

# 40. Excel

Operational reference data frequently arrives as Excel workbooks.

Supporting `.xlsx` provides high value.

Preferred dependency:

```text
openpyxl
```

Reasons:

- mature;
- widely deployed;
- designed for XLSX;
- usable without Pandas;
- supports read-only workbook mode.

---

# 41. Excel dependency policy

Excel support should be an optional dependency.

Recommended:

```toml
[project.optional-dependencies]
excel = ["openpyxl>=3.1,<4"]
```

Core install:

```bash
pip install pyingestkit
```

Excel install:

```bash
pip install "pyingestkit[excel]"
```

Do not impose OpenPyXL on consumers who never ingest spreadsheets.

---

# 42. ExcelParser

Conceptual surface:

```python
ExcelParser(
    sheet_name=0,
    header_row=1,
    data_only=True,
    read_only=True,
)
```

Potential features:

```text
sheet selection
header row selection
empty-row handling
formula result mode
read-only workbook loading
```

---

# 43. Excel structural semantics

The parser may:

- choose a worksheet;
- read a header row;
- map cells to fields;
- preserve cell values returned by OpenPyXL;
- reject duplicate/empty ambiguous headers according to documented rules.

It should not:

- normalize column labels to business names;
- trim all strings automatically;
- map codes;
- evaluate business formulas;
- enrich rows;
- reinterpret identifiers.

---

# 44. Excel formulas

Default recommendation:

```text
data_only=True
```

This reads cached formula results where available.

PyIngestKit should NOT become an Excel formula calculation engine.

Document clearly that stale/missing cached values are an input artifact limitation.

---

# 45. Excel date handling

OpenPyXL may return Python date/datetime values.

Preserve them.

Do not automatically convert:

```text
datetime → ISO string
```

inside the parser.

Serialization into reports/manifests may use ISO formatting at the serialization boundary.

---

# 46. Excel workbook security

Spreadsheet ingestion can expose large or malformed workbook risks.

Use:

```text
read_only=True
```

by default where practical.

Do not load macros or execute workbook content.

Only XLSX is targeted initially.

`.xls` legacy binary format is not a V0.3 requirement.

---

# 47. Parquet

Parquet is important for data-engineering usage and efficient interchange.

Preferred backend:

```text
PyArrow
```

But it must remain optional.

---

# 48. Parquet dependency policy

Recommended:

```toml
parquet = ["pyarrow>=16,<24"]
```

Installation:

```bash
pip install "pyingestkit[parquet]"
```

The upper bound should be reviewed based on supported Python versions and actual API compatibility during implementation.

---

# 49. Why PyArrow

Advantages:

- mature Parquet implementation;
- native Arrow schema;
- good performance;
- widespread ecosystem adoption;
- no Pandas requirement;
- well-supported Python wheels.

PyArrow is infrastructure, not the framework Dataset API.

---

# 50. ParquetParser boundary

Conceptual:

```python
ParquetParser().parse(raw_artifact)
```

Internal path:

```text
RawArtifact
    ↓
PyArrow Parquet reader
    ↓
Arrow Table
    ↓
row mappings
    ↓
Dataset
```

The Arrow Table is an implementation detail.

---

# 51. Avoid leaking Arrow types

Core public API should not require:

```python
pyarrow.Table
```

for ordinary Dataset operations.

Otherwise users without the Parquet extra would inherit Arrow coupling throughout the framework API.

---

# 52. Parquet and large datasets

This is the main architectural warning for V0.3.

Converting a multi-GB Parquet file into:

```python
list[dict]
```

is not scalable.

The first implementation therefore needs explicit scope documentation.

Options:

```text
A. impose/document a materialization boundary for V0.3
B. prematurely build full streaming Dataset
```

Recommendation:

```text
choose A
```

and prepare architecture for B later.

---

# 53. Materialized Dataset boundary

V0.3 documentation should state:

```text
Dataset is intended for bounded structured ingestion workloads.
```

Do not claim arbitrarily large dataset support.

Job packs handling very large Parquet assets may:

```text
RawArtifact
    ↓
custom Arrow/Polars/DuckDB path
```

without forcing that engine into the framework core.

---

# 54. Future Dataset evolution

Potential future abstractions:

```text
Dataset
BufferedDataset
StreamingDataset
```

or capability protocols:

```python
class DatasetLike(Protocol): ...
```

Do NOT implement them only because they may be useful later.

V0.3 simply avoids making them impossible.

---

# 55. Profiling future streaming compatibility

Avoid profiler code that requires random row access.

Prefer algorithms expressible as:

```text
for row in dataset:
    update counters
```

This allows later reuse against a streamed row source.

---

# 56. Validation future streaming compatibility

Many field validations can also operate row by row.

However:

```text
uniqueness
distinct count
duplicate detection
```

require state.

V0.3 may use exact in-memory sets.

Future large-scale variants may expose approximate/external state explicitly.

---

# 57. Public API organization

Recommended package layout:

```text
src/pyingestkit/
│
├── dataset.py
│
├── parsers/
│   ├── base.py
│   ├── csv.py
│   ├── json.py
│   ├── ndjson.py
│   ├── excel.py
│   └── parquet.py
│
├── contracts/
│   └── dataset.py
│
├── profiling/
│   ├── __init__.py
│   ├── models.py
│   └── profiler.py
│
├── validation/
│   ├── result.py
│   └── report.py
│
└── quality/
    ├── __init__.py
    └── report.py
```

---

# 58. `profiling` vs `quality`

Recommended separation:

```text
profiling/
    computation + profile models

quality/
    report aggregation / serialization
```

Do not create dozens of tiny modules prematurely.

---

# 59. Dependency import policy

Optional-format modules should fail clearly when used without their extras.

Example:

```python
try:
    import openpyxl
except ImportError as exc:
    raise OptionalDependencyError(
        "Excel support requires pyingestkit[excel]"
    ) from exc
```

But avoid importing optional dependencies eagerly from top-level package import paths if that makes:

```python
import pyingestkit
```

fail without extras.

---

# 60. Optional dependency exception

A dedicated error may be useful:

```text
OptionalDependencyError
```

or the existing configuration/dependency error hierarchy may be reused.

Prefer reuse if semantics are already adequate.

Do not add exception classes simply for naming aesthetics.

---

# 61. Parser registry question

V0.3 should NOT add a magic parser registry unless there is a concrete requirement.

Explicit code remains preferable:

```python
CsvParser()
JsonParser()
NdjsonParser()
ExcelParser()
ParquetParser()
```

A registry can be added later if configuration-driven parser construction demands it.

---

# 62. Declarative configuration question

V0.3 parser additions do not require immediately extending YAML into:

```yaml
parser:
  type: parquet
  options: ...
```

The framework already permits job-pack Python definitions.

Configuration DSL expansion should happen only when a stable cross-format schema is evident.

---

# 63. Contract identity

Quality reports benefit from identifying the contract used.

Possible V0.3 addition:

```python
DatasetContract(
    id="postal_codes.v1",
    ...
)
```

However this changes the core constructor surface.

Recommendation for A1:

- consider optional `id: str | None`;
- add only if report design clearly requires it;
- otherwise let the job/report layer supply the contract identifier.

Do not make identity mandatory.

---

# 64. Report schema version

Every machine-readable quality report should contain:

```text
schema_version
```

Starting with:

```text
1
```

This is distinct from:

```text
PyIngestKit package version
```

because report schemas may evolve on a different compatibility cycle.

---

# 65. JSON serialization

Quality report models should expose ordinary JSON-compatible dictionaries.

Date/datetime values should serialize consistently to ISO-8601.

Unknown application objects must not be silently converted to unreliable `repr()` payloads in long-term evidence.

Where unsupported values appear, prefer bounded/type-aware representations.

---

# 66. Sensitive data in profiles

Profiles must not expose raw unique values by default.

Allowed:

```text
null_count
distinct_count
min numeric value
max numeric value
min/max length
observed types
```

Avoid by default:

```text
sample email addresses
sample names
first 100 distinct values
```

That makes profiling safer for operational datasets.

---

# 67. Sensitive data in validation

`allowed_values` error messages should avoid dumping a gigantic allowed list.

Prefer:

```text
Field 'status' contains a value outside the declared allowed set
```

rather than:

```text
value X not in [thousands of values...]
```

Likewise previews are bounded and redact known secret fields.

---

# 68. Regex safety

User-supplied regex can exhibit pathological behavior.

V0.3 will not build a regex sandbox.

Mitigations:

- compile once during contract initialization;
- document that patterns are trusted job configuration/code;
- do not accept arbitrary untrusted remote regex configuration by default.

---

# 69. Excel resource limits

Potential malformed input risks:

```text
huge sheets
huge shared strings
many empty styled rows
```

V0.3 may expose conservative parser options such as:

```text
max_rows
max_columns
```

only if implementation/testing shows clear need.

Avoid speculative knobs without enforcement.

---

# 70. Parquet resource limits

PyArrow can materialize substantial memory.

Useful future/parser options:

```text
columns
row_limit
```

For V0.3 Beta 2, start with a minimal parser and document bounded-dataset expectations.

Do not pretend a Python list-of-mappings result is appropriate for unlimited files.

---

# 71. NDJSON resource limits

Since Dataset materializes rows, full line streaming does not eliminate final memory cost.

Still, incremental parsing avoids a redundant whole-document JSON representation.

This makes NDJSON the best format for validating future streaming-friendly algorithm structure.

---

# 72. Testing strategy

Retain three layers:

```text
unit
contract
integration
```

All ordinary tests remain offline.

---

# 73. Contract V2 tests

Required examples:

```text
allowed_values pass/fail
regex pass/fail
min/max numeric
min/max length
composite uniqueness
primary key null
primary key duplicate
issue_limit
no mutation
backward-compatible V0.2 constructor
```

---

# 74. Profiling tests

Required:

```text
empty dataset
single row
null counts
mixed runtime types
distinct counts
duplicate rows
nested unhashable values
numeric min/max
string min/max length
deterministic output
no value samples leaked
```

---

# 75. NDJSON tests

Required:

```text
valid rows
blank lines
invalid JSON
scalar line rejection
array line rejection
native types
line number in safe error context
source_artifact_id retained
```

---

# 76. Excel tests

Use locally generated workbooks.

Tests must NOT rely on downloading fixtures.

Required:

```text
single sheet
sheet selection
headers
empty cells
boolean
integer
float
date/datetime
duplicate header rejection
missing sheet
formula/cache behavior where practical
optional dependency boundary
```

---

# 77. Parquet tests

Generate Parquet fixtures at test time using PyArrow when the extra is available.

Required:

```text
basic table
nulls
native primitive types
column order
source_artifact_id
optional dependency boundary
```

Tests requiring PyArrow belong to the optional-dependency CI path.

---

# 78. CI optional dependency strategy

Main test matrix may install:

```text
.[dev]
```

with dev including the supported optional format dependencies during repository verification.

Consumer package smoke tests should also verify:

```text
core install without Excel/Parquet
excel extra
parquet extra
```

This catches accidental eager imports.

---

# 79. Wheel smoke expansion

V0.2 wheel smoke executes:

```text
local file
HTTP CSV
HTTP JSON
```

V0.3 stable should add reference jobs for new format/quality surfaces.

Possible final set:

```text
demo.local_file
demo.http_csv
demo.http_json
demo.ndjson_quality
demo.excel_quality
demo.parquet_quality
```

Not all need to ship in Alpha 1.

---

# 80. Reference quality job

A useful V0.3 reference slice:

```text
fixture NDJSON
    ↓
RawArtifact
    ↓
NdjsonParser
    ↓
Dataset
    ↓
DatasetContract V2
    ↓
DatasetProfiler
    ↓
validation.json
profile.json
    ↓
manifest
```

This provides an E2E proof without requiring external network access.

---

# 81. Excel reference job

Use a generated deterministic workbook rather than committing a binary fixture if possible.

That proves:

```text
OpenPyXL optional dependency
        ↓
workbook
        ↓
RawArtifact
        ↓
ExcelParser
        ↓
Dataset
```

Tests should generate bytes in memory or in a temporary path.

---

# 82. Parquet reference job

Likewise create a tiny deterministic Parquet payload using PyArrow in the test/demo fixture layer.

The framework itself should remain unaware that the bytes were generated by a fixture.

---

# 83. Logging

New quality operations should use existing stdlib logging infrastructure.

Example useful fields:

```text
run_id
job_id
step
rows
fields
errors
warnings
report_path
```

Do not log complete rows or profile samples.

---

# 84. Metrics posture

V0.3 may make metrics structurally available through events/report values but should not add Prometheus/OpenTelemetry dependencies.

Examples:

```text
rows_profiled
validation_errors
validation_warnings
duplicate_rows
```

External adapters can map these later.

---

# 85. Performance targets

V0.3 should have simple regression-oriented targets, not marketing benchmarks.

Examples:

- contract validation should remain linear in row count for ordinary field constraints;
- profiling should use one primary scan where practical;
- regex should be compiled once;
- Excel uses read-only mode;
- NDJSON does not parse an unnecessary enclosing document;
- Parquet delegates decoding to PyArrow.

---

# 86. Complexity targets

Avoid turning `DatasetContract.validate()` into one giant 500-line function.

Recommended internal decomposition:

```text
_validate_row_count
_validate_schema
_validate_field
_validate_allowed_values
_validate_pattern
_validate_range
_validate_length
_validate_uniqueness
_validate_composite_uniqueness
_validate_primary_key
```

But helpers should reflect real concerns rather than each being a two-line abstraction.

---

# 87. Error hierarchy

Continue using framework exceptions:

```text
PyIngestKitError
ConfigurationError
ValidationError
ParseError
```

Parser input failures → `ParseError`.

Missing optional dependency → configuration/dependency error.

Validation violations → `ValidationResult`, not parser exceptions.

---

# 88. Parser failure contract

Examples:

```text
invalid NDJSON syntax → ParseError
missing Excel sheet → ParseError or configuration error based on constructor semantics
malformed XLSX → ParseError
invalid Parquet → ParseError
```

Do not leak backend-specific exception classes as the stable framework contract.

The original exception should remain available through exception chaining.

---

# 89. Backend exception chaining

Example:

```python
try:
    ...
except SomeOpenpyxlError as exc:
    raise ParseError("Unable to parse Excel workbook") from exc
```

Same for PyArrow.

This preserves diagnostic depth without exposing backend internals as API semantics.

---

# 90. Dataset field ordering

All new parsers must preserve stable field order.

NDJSON:

```text
first record keys + subsequently discovered keys
```

or the existing Dataset inference rule.

Excel:

```text
header order
```

Parquet:

```text
schema column order
```

Do not sort fields alphabetically unless the existing Dataset contract already requires it.

---

# 91. Sparse NDJSON records

Example:

```json
{"id": 1, "name": "A"}
{"id": 2, "country": "FR"}
```

Dataset may contain a union schema while rows remain sparse, matching current JSON parser semantics.

Do not inject explicit `None` merely to rectangularize rows unless Dataset already specifies that behavior.

---

# 92. Excel empty rows

Recommended default:

```text
skip completely empty rows
```

because spreadsheet used ranges often contain empty trailing rows.

But a row containing:

```text
"", None, None
```

needs a documented definition of empty.

Prefer:

```text
all cells are None
```

rather than stripping strings.

---

# 93. Excel headers

Header cells should be required to produce unambiguous field names.

Recommended initial behavior:

```text
None header      → ParseError
empty string     → accepted only if explicitly decided; recommended reject
duplicate header → ParseError
```

Do not invent names like:

```text
Unnamed: 3
```

That is a dataframe convenience, not structural fidelity.

---

# 94. Parquet nested types

PyArrow may return nested Python structures.

V0.3 can preserve:

```text
list
struct → dict
```

where `to_pylist()` naturally provides them.

Do not flatten nested data automatically.

Dataset contracts can validate top-level fields first.

---

# 95. Parquet decimal types

PyArrow may return `decimal.Decimal`.

Preserve it.

Do not cast to float automatically.

This avoids precision loss.

---

# 96. Parquet timestamps

Preserve Python datetime representations returned by Arrow conversion.

Timezone semantics should not be silently discarded.

---

# 97. Quality report writer

Potential API:

```python
QualityReportWriter.write(
    validation=result,
    profile=profile,
    context=context,
)
```

But avoid a class if simple serialization functions plus ArtifactStore are sufficient.

The important abstraction is the **report schema**, not object-oriented ceremony.

---

# 98. ArtifactStore integration

Reuse:

```python
artifact_store.write_json(...)
```

This already provides the right serialization/publication boundary.

Do not bypass ArtifactStore with direct `Path.write_text()` from Runner.

---

# 99. Atomic report writes

Because ArtifactStore JSON writes are atomic, quality reports inherit crash-safe replacement semantics.

That is desirable because a half-written `validation.json` is misleading operational evidence.

---

# 100. Report filename policy

Initial filenames:

```text
reports/validation.json
reports/profile.json
```

Question: multiple validation steps may exist.

Possible policy:

```text
reports/<step>/validation.json
```

or:

```text
reports/validation-<step>.json
```

V0.3-a2 must resolve this before stable release.

Recommended general structure:

```text
reports/<step>/validation.json
reports/<step>/profile.json
```

if multiple quality-producing steps become common.

For initial reference jobs with a single structured Dataset validation step, flat paths are acceptable only if overwrite behavior is explicitly prevented.

---

# 101. Multiple ValidationResults

Runner already extracts nested `ValidationResult` objects.

Quality report generation must define:

```text
one report per result
```

versus:

```text
one aggregated run report
```

Recommended V0.3:

```text
one report document may contain multiple validation result entries
```

or use per-step reports.

Do not silently overwrite.

---

# 102. Profiling invocation ownership

Should Runner automatically profile every Dataset?

Recommendation:

```text
NO
```

Profiling may cost memory/time and should be explicit in jobs or configuration.

Runner should observe/persist `DatasetProfile` when produced, analogous to `ValidationResult`.

This preserves composability.

---

# 103. DatasetProfile runtime observation

Parallel to validation:

```text
Step output
   ↓
DatasetProfile discovered
   ↓
manifest report reference
   ↓
profile.json
   ↓
PROFILE_COMPLETED
```

A profile never fails the run by itself.

Profiler exceptions fail the producing step as ordinary execution errors.

---

# 104. QualityReport aggregation

A convenient immutable model may combine:

```text
validation
profile
```

Example:

```python
QualityReport(
    validation=validation_result,
    profile=dataset_profile,
)
```

This should remain optional; Runner can observe the individual types if simpler.

---

# 105. Contract versioning

Do not invent a remote contract registry in V0.3.

Jobs can version contracts in code:

```python
POSTAL_CODE_CONTRACT_V1 = DatasetContract(...)
```

or attach a simple identifier to report metadata.

Central contract discovery can be revisited after real usage.

---

# 106. Reproducibility

Quality evidence should be reproducible from:

```text
same RawArtifact
+
same Parser configuration
+
same normalization code
+
same contract
+
same PyIngestKit version
```

This becomes especially important before V0.4 replay/versioning.

---

# 107. Provenance linkage

Profile/validation reports should retain:

```text
source_artifact_id
```

when the Dataset has one.

This creates a strong chain:

```text
source URL
  ↓
RawArtifact sha256
  ↓
Dataset
  ↓
Quality evidence
```

---

# 108. Diff/replay preparation

V0.3 should not implement V0.4 diff/replay, but its reports should not obstruct it.

In particular:

```text
report values deterministic
report schema versioned
source artifact linked
parser configuration reconstructable by job code/config
```

These enable later replay comparisons.

---

# 109. Serialization schema discipline

Avoid storing Python implementation details such as:

```text
<class 'str'>
```

Prefer stable labels:

```text
str
int
float
bool
datetime
```

Likewise use explicit JSON keys rather than serializing dataclass internals blindly.

---

# 110. Schema stability hierarchy

V0.3 has three layers of compatibility:

```text
1. Python public API
2. manifest/report JSON schema
3. internal implementation
```

Internal implementation may evolve freely.

Public API/report schemas require compatibility discipline.

---

# 111. Report schema fixtures

Add golden-ish structural tests for report JSON keys.

Do not compare timestamps/durations byte-for-byte.

Compare stable structure and values.

---

# 112. No arbitrary pickles

Never persist Dataset/Profile/ValidationResult using pickle.

Reasons:

```text
security
portability
version coupling
language coupling
```

Use JSON-compatible explicit schemas for evidence.

---

# 113. Excel and XML confusion

V0.3 Excel support is XLSX only.

Although XLSX internally contains XML, this does not mean PyIngestKit has a general XML parser.

General XML remains later work if justified.

---

# 114. NDJSON naming

Use:

```text
NdjsonParser
```

rather than ambiguous variants such as:

```text
JsonLinesParser
JSONLParser
```

unless ecosystem conventions strongly justify aliases.

Avoid multiple aliases in the first release.

---

# 115. Excel naming

Use:

```text
ExcelParser
```

with explicit documented supported format:

```text
XLSX
```

Avoid `XlsxParser` unless precision outweighs usability.

---

# 116. Parquet naming

Use:

```text
ParquetParser
```

Backend remains internal.

Do not name it:

```text
PyArrowParquetParser
```

because that leaks implementation choice into the public framework vocabulary.

---

# 117. Dependency versions

During implementation, pin compatibility ranges rather than exact patch versions for runtime extras.

Example:

```text
openpyxl >=3.1,<4
pyarrow >=16,<24
```

Exact resolution belongs to consumer lockfiles/CI environments.

---

# 118. Python support

Retain:

```text
Python 3.11
Python 3.12
Python 3.13
```

Before adding PyArrow to optional CI, confirm wheels exist for all supported versions in the chosen dependency range.

If a backend cannot support one Python version, do not silently reduce core Python support; isolate optional-extra compatibility explicitly.

---

# 119. Platform support

Primary automated release confidence:

```text
Linux CI
```

Wheel dependencies should use mature cross-platform projects.

Pure Python PyIngestKit wheel remains:

```text
py3-none-any
```

even though PyArrow itself is platform-specific.

---

# 120. Documentation architecture

New docs:

```text
docs/architecture/quality-formats-v0.3.md

docs/guides/dataset-contracts-v2.md
docs/guides/dataset-profiling.md
docs/guides/quality-reports.md
docs/guides/ndjson.md
docs/guides/excel.md
docs/guides/parquet.md
```

Some guides may be merged if individually too small.

---

# 121. ADR set

Recommended V0.3 ADRs:

```text
ADR-028 — Dataset Contracts V2 semantics
ADR-029 — Dataset profiling is descriptive, not semantic inference
ADR-030 — Quality reports are run artifacts
ADR-031 — NDJSON structural parser
ADR-032 — Excel via optional OpenPyXL backend
ADR-033 — Parquet via optional PyArrow backend
ADR-034 — Materialized Dataset boundary / future streaming compatibility
```

The exact split may be reduced if decisions are tightly related.

---

# 122. Alpha 1 scope

`V0.3.0-a1 — Quality Contracts V2`

Only implement:

```text
FieldContract V2
DatasetContract V2
ValidationIssue V2 where necessary
unit tests
contract tests
ADR
API docs
```

Do NOT implement in A1:

```text
profiling
reports
NDJSON
Excel
Parquet
streaming
```

This keeps the first alpha easy to review.

---

# 123. Alpha 1 implementation order

Recommended:

```text
1. freeze rule names
2. extend FieldContract
3. constructor invariants
4. allowed values
5. regex
6. min/max
7. length
8. composite uniqueness
9. primary key semantics
10. issue limit
11. richer issue metadata
12. tests
13. API exports
14. docs
```

---

# 124. Rule names

Recommended stable rule vocabulary:

```text
dataset.min_rows
dataset.max_rows
dataset.extra_field
dataset.composite_unique
dataset.primary_key

field.required
field.null
field.type
field.unique
field.unique_unhashable
field.allowed_values
field.pattern
field.min_value
field.max_value
field.min_length
field.max_length
```

Avoid renaming existing V0.2 rules.

---

# 125. Regex naming

Prefer rule:

```text
field.pattern
```

and constructor field:

```text
pattern
```

rather than mixing:

```text
regex
regexp
pattern
```

The implementation should choose one public vocabulary.

Recommended:

```python
pattern: str | None
```

---

# 126. Allowed-values representation

Use immutable input internally.

Public constructor may accept:

```python
Collection[Any]
```

but freeze/copy it so later caller mutation cannot change contract semantics.

Avoid requiring hashability because allowed values may technically include values such as lists, though supporting complex membership is not essential.

For predictable behavior, V0.3 can restrict to ordinary scalar values and document it.

---

# 127. Range constraints initialization

If both provided and comparable:

```text
min_value <= max_value
```

validate at contract construction.

If generic `Any` prevents reliable constructor comparison, avoid forcing unsafe comparisons there and validate values independently.

---

# 128. Length invariant

Require:

```text
min_length >= 0
max_length >= 0
min_length <= max_length
```

Invalid contract definition should fail fast with `ValueError` or configuration error consistent with existing dataclass constructors.

---

# 129. Composite constraint definition

Require:

```text
at least 2 fields per composite unique
all referenced fields declared or deliberately support schema-only fields
no duplicate field inside one composite constraint
```

Recommended simplification:

```text
all referenced fields must be declared in contract.fields
```

This catches typos at definition time.

---

# 130. Primary key definition

Allow:

```text
1..N fields
```

All fields must be declared.

Do not automatically mutate their individual `nullable` or `unique` properties.

Primary-key validation is a distinct dataset-level rule.

---

# 131. Duplicate error cardinality

For duplicate values, report each duplicate row after the first occurrence.

Example:

```text
rows 4, 9, 12 same key
```

issues:

```text
row 9 duplicates row 4
row 12 duplicates row 4
```

This matches current field uniqueness semantics.

---

# 132. Null primary-key behavior

If key contains null:

```text
dataset.primary_key
```

Do not emit the same conceptual violation as both:

```text
field.null
AND
dataset.primary_key
```

unless individual FieldContract also explicitly says `nullable=False`.

Then both rules are legitimate because two declared constraints were violated.

---

# 133. Issue-limit ordering

Issue ordering must remain deterministic.

Recommended validation order:

```text
row counts
schema
field contracts in declaration order
rows in input order
dataset composite constraints in declaration order
primary key
```

The issue limit truncates this deterministic stream.

---

# 134. Alpha 1 backward compatibility

Existing V0.2 tests must remain unchanged where possible.

At minimum:

```python
FieldContract("id")
DatasetContract()
```

must still construct successfully.

Existing rule codes remain stable.

---

# 135. Alpha 2 scope

`V0.3.0-a2 — Dataset Profiling + Quality Reports`

Implement:

```text
DatasetProfiler
DatasetProfile
FieldProfile
Validation report schema
Profile report schema
ArtifactStore integration
manifest references
runtime events
status inspection where useful
docs
```

No new parser dependency in Alpha 2.

---

# 136. Profiling algorithm

Prefer one pass for:

```text
row_count
field null counts
observed types
min/max
length ranges
distinct tracking
row duplicate tracking
```

Exact distinct tracking uses memory proportional to cardinality. This is acceptable under the V0.3 materialized Dataset boundary.

Document it.

---

# 137. Mixed numeric types

Python:

```python
bool
```

is a subclass of:

```python
int
```

Profiler type labels must check `bool` before `int` to avoid reporting booleans as integers.

Validation `isinstance(value, int)` retains ordinary Python semantics unless V0.3 explicitly decides otherwise.

Do not casually change V0.2 type behavior.

---

# 138. Numeric range profiling

For homogeneous/comparable numeric values:

```text
min_value
max_value
```

For heterogeneous incomparable values:

```text
omit range
```

Do not crash profiling.

Do not stringify values solely to compare them.

---

# 139. Datetime profiling

Datetime/date min/max may be useful but introduces timezone comparability complexity.

V0.3 can restrict min/max to numeric types initially.

Observed type remains enough for date/datetime fields.

This is safer than partially correct comparisons.

---

# 140. Field presence semantics

Dataset rows may be sparse.

Profile should distinguish:

```text
missing field
```

from:

```text
field present with None
```

Potential metrics:

```text
missing_count
null_count
```

Recommended if easy to support because sparse JSON/NDJSON makes this meaningful.

At minimum document whether null count includes missing.

---

# 141. Profile structure recommendation

```python
@dataclass(frozen=True, slots=True)
class FieldProfile:
    name: str
    present_count: int
    missing_count: int
    null_count: int
    non_null_count: int
    distinct_count: int | None
    observed_types: tuple[str, ...]
    min_value: int | float | None
    max_value: int | float | None
    min_length: int | None
    max_length: int | None
```

---

# 142. DatasetProfile structure recommendation

```python
@dataclass(frozen=True, slots=True)
class DatasetProfile:
    row_count: int
    field_count: int
    duplicate_row_count: int
    fields: tuple[FieldProfile, ...]
```

Use ordered tuple rather than mutable dict as the core evidence representation.

`as_dict()` may expose JSON-compatible mapping output.

---

# 143. Report generator purity

Profile computation:

```text
Dataset → DatasetProfile
```

Report serialization:

```text
DatasetProfile → JSON-compatible mapping
```

Artifact persistence:

```text
mapping → ArtifactStore
```

Keep these separately testable.

---

# 144. Beta 1 scope

`V0.3.0-b1 — NDJSON + Excel`

Implement:

```text
NdjsonParser
ExcelParser
excel optional extra
parser tests
quality integration tests
reference jobs if stable enough
```

Why together?

NDJSON is dependency-free while Excel validates the optional dependency design before Parquet introduces a much heavier dependency.

---

# 145. Beta 2 scope

`V0.3.0-b2 — Parquet`

Implement:

```text
ParquetParser
parquet optional extra
PyArrow CI path
Parquet tests
large-data boundary documentation
```

Do not expand into Arrow-native Dataset APIs.

---

# 146. RC1 scope

`V0.3.0-rc1 — Quality & Formats E2E`

Connect:

```text
HTTP/local fixture
       ↓
RAW
       ↓
parser
       ↓
Dataset
       ↓
Contract V2
       ↓
Profiler
       ↓
Quality Reports
       ↓
Manifest / Metadata / Events
```

Run all reference jobs in wheel-installed environment.

---

# 147. Stable scope

`V0.3.0`

Stable promotion requires:

```text
API contract frozen
report schema documented
all supported Python versions green
optional format extras green
security gate green
clean wheel install green
reference jobs green
docs complete
checksums produced
```

---

# 148. Version sequence

```text
0.3.0a1
  ↓
0.3.0a2
  ↓
0.3.0b1
  ↓
0.3.0b2
  ↓
0.3.0rc1
  ↓
0.3.0
```

Do not release unnecessary intermediate alphas if implementation does not justify them, but preserve this review structure during development.

---

# 149. Git strategy

Recommended branch:

```text
feat/v0.3-quality-formats
```

Implementation commits should map to coherent lots:

```text
feat(contracts): ...
feat(profiling): ...
feat(reports): ...
feat(ndjson): ...
feat(excel): ...
feat(parquet): ...
```

Avoid one 5,000-line opaque commit if practical.

---

# 150. Lot 1

```text
V0.3.0-a1
Quality Contracts V2
```

Deliver:

```text
extended FieldContract
extended DatasetContract
bounded issue behavior
richer ValidationIssue
unit tests
contract tests
ADR-028
```

---

# 151. Lot 2

```text
A1 hardening
```

Deliver:

```text
edge cases
unhashable values
mixed types
issue ordering
secret preview redaction
backward compatibility
```

---

# 152. Lot 3

```text
V0.3.0-a2
Profile models
```

Deliver:

```text
FieldProfile
DatasetProfile
canonicalization helper
serialization
```

---

# 153. Lot 4

```text
Profiler engine
```

Deliver:

```text
DatasetProfiler
exact counters
deterministic type ordering
numeric/string stats
duplicate detection
```

---

# 154. Lot 5

```text
Quality reports
```

Deliver:

```text
validation report
profile report
schema_version
safe JSON serialization
```

---

# 155. Lot 6

```text
Runtime report integration
```

Deliver:

```text
ArtifactStore writes
manifest references
PROFILE_COMPLETED
QUALITY_REPORT_WRITTEN
status visibility
```

---

# 156. Lot 7

```text
V0.3.0-b1
NdjsonParser
```

Deliver:

```text
stdlib NDJSON parser
safe line errors
native JSON types
unit tests
```

---

# 157. Lot 8

```text
Excel optional dependency
```

Deliver:

```text
[excel] extra
lazy backend import
missing-extra error tests
```

---

# 158. Lot 9

```text
ExcelParser
```

Deliver:

```text
XLSX
sheet selection
header row
read_only
data_only
empty-row handling
native cell values
```

---

# 159. Lot 10

```text
Excel integration
```

Deliver:

```text
generated workbook fixtures
DatasetContract V2
profiling
reports
```

---

# 160. Lot 11

```text
V0.3.0-b2
Parquet optional dependency
```

Deliver:

```text
[parquet] extra
PyArrow lazy loading
CI compatibility
```

---

# 161. Lot 12

```text
ParquetParser
```

Deliver:

```text
Arrow Table
→ Python rows
→ Dataset
```

---

# 162. Lot 13

```text
Parquet integration
```

Deliver:

```text
generated Parquet fixture
DatasetContract
profiling
reports
```

---

# 163. Lot 14

```text
Reference quality job
```

Deliver one deterministic end-to-end job demonstrating the full quality lifecycle.

---

# 164. Lot 15

```text
CLI/Status integration
```

Ensure operators can discover:

```text
validation status
profile report path
quality report path
```

without opening SQLite manually.

---

# 165. Lot 16

```text
RC hardening
```

Run:

```text
all existing V0.1/V0.2 tests
V0.3 tests
strict typing
Ruff
Bandit
pip-audit
package build
wheel smoke
```

---

# 166. Lot 17

```text
Cross-version compatibility
```

Verify:

```text
V0.2 job code continues to work
old DatasetContract constructors work
old CSV/JSON behavior unchanged
manifest additive fields do not break existing consumers
```

---

# 167. Lot 18

```text
Release packaging
```

Produce:

```text
source ZIP
sdist
wheel
demo-job sdist
demo-job wheel
validation evidence
SHA256SUMS
```

---

# 168. Definition of Done — Contracts V2

Complete when:

```text
all new rule semantics documented
existing rules preserved
new tests green
validation does not mutate Dataset
issue ordering deterministic
issue volume bounded
no secret row dumps
```

---

# 169. Definition of Done — Profiling

Complete when:

```text
profile deterministic
null/distinct/type metrics correct
nested values do not crash duplicate detection
no raw distinct samples by default
immutable result models
```

---

# 170. Definition of Done — Reports

Complete when:

```text
schema_version present
validation JSON stable
profile JSON stable
manifest references report
atomic write
JSON-compatible values
source/run correlation
```

---

# 171. Definition of Done — NDJSON

Complete when:

```text
line-oriented parser
safe malformed-line errors
native JSON values
blank line policy documented
Dataset source linkage
```

---

# 172. Definition of Done — Excel

Complete when:

```text
XLSX parse works
OpenPyXL optional
sheet selection works
header semantics explicit
read-only mode
no business normalization
tests use generated local fixtures
```

---

# 173. Definition of Done — Parquet

Complete when:

```text
PyArrow optional
Parquet decode works
column order preserved
nested/native values handled predictably
bounded Dataset warning documented
no Arrow dependency leaked into core public API
```

---

# 174. Definition of Done — V0.3 stable

```text
Python 3.11     green
Python 3.12     green
Python 3.13     green

Ruff            green
Mypy            green
Bandit          green
pip-audit       green

core smoke      green
excel smoke     green
parquet smoke   green

wheel smoke     green
reference jobs  green

API docs        complete
ADRs            accepted
checksums        verified
```

---

# 175. Security checklist

V0.3 release review must verify:

- validation messages do not leak full sensitive rows;
- profile reports do not expose raw distinct values;
- NDJSON parse errors do not dump full lines;
- Excel does not execute macros;
- Excel formulas are not evaluated by PyIngestKit;
- backend exceptions are safely wrapped;
- report paths cannot escape run directory;
- optional dependencies do not cause insecure fallback logic;
- no pickle serialization;
- no arbitrary code execution from contract definitions.

---

# 176. Performance checklist

Review:

```text
regex compilation once
single-pass profiling where practical
no repeated Dataset.to_rows copies
no quadratic uniqueness loops
read-only Excel
incremental NDJSON parsing
PyArrow-backed Parquet decode
issue-limit enforcement
```

---

# 177. Compatibility checklist

Review against V0.2:

```text
Dataset constructor
Dataset iteration
CsvParser
JsonParser
FieldContract existing args
DatasetContract existing args
ValidationIssue existing constructor
ValidationResult
Runner validation observation
status command
manifest existing keys
```

---

# 178. API naming freeze

Before RC1 verify there are no accidental synonyms like:

```text
regex + pattern
issue_limit + max_issues
composite_unique + unique_together
column_count + field_count
```

Choose one public term for each concept.

Aliases may be more harmful than useful before V1.

---

# 179. Recommended final naming

Recommended:

```text
FieldContract.pattern
FieldContract.allowed_values
FieldContract.min_value
FieldContract.max_value
FieldContract.min_length
FieldContract.max_length

DatasetContract.unique_together
DatasetContract.primary_key
DatasetContract.max_issues

DatasetProfile.field_count
DatasetProfile.duplicate_row_count
```

This vocabulary is Pythonic and reasonably concise.

---

# 180. Why not Pandera

Pandera is valuable for dataframe-oriented validation.

PyIngestKit deliberately keeps a lower-level engine-neutral Dataset contract.

Users may use:

```text
PyIngestKit
  ↓
Dataset
  ↓
Pandas
  ↓
Pandera
```

when their application needs that ecosystem.

It should not be mandatory for every ingestion job.

---

# 181. Why not Great Expectations

Great Expectations solves broader data-quality and expectation-suite workflows.

PyIngestKit needs a compact ingestion contract, not a second quality platform.

Interop later is preferable to embedding a large DSL now.

---

# 182. Why not Polars as Dataset

Polars would provide high performance but would make one engine part of the public interchange contract.

Job packs can convert explicitly when appropriate.

This decision may be revisited only with substantial workload evidence.

---

# 183. Why not Arrow as Dataset now

Arrow is attractive especially for Parquet, but making it the universal Dataset would impose:

```text
large dependency
platform wheels
Arrow type semantics
memory model decisions
```

on CSV/JSON-only users.

V0.3 uses Arrow at the Parquet adapter boundary instead.

---

# 184. Why profiling belongs in framework

Unlike business normalization, descriptive metrics are generic across ingestion domains.

Examples:

```text
row count
null count
distinct count
duplicates
observed types
```

These are useful for:

```text
postal codes
NAF
ROME
company registries
financial references
application exports
```

without becoming domain-specific.

---

# 185. Why reports belong in framework

Validation without durable evidence is operationally weak.

A job should leave behind:

```text
what was fetched
what was parsed
what quality was observed
what was published
```

This is central to PyIngestKit's product promise.

---

# 186. V0.3 lifecycle after completion

```text
DISCOVER
    ↓
FETCH
    ↓
RAW
    ↓
HASH / PROVENANCE
    ↓
PARSE
    ↓
NORMALIZE
    ↓
VALIDATE
    ↓
PROFILE
    ↓
QUALITY REPORTS
    ↓
PUBLISH
    ↓
LOAD
    ↓
MANIFEST / METRICS / RUN STATUS
```

Not every job is required to execute every optional stage.

---

# 187. Roadmap relationship

```text
V0.1
Foundation

V0.2
Acquisition

V0.3
Quality & Formats

V0.4
Diff / Replay / Versioning

V0.5
Persistence targets

V0.6
Object storage if justified

V1
Stable framework contract
```

---

# 188. Preparation for V0.4

V0.3 provides several prerequisites for V0.4:

```text
immutable RAW artifacts
stable SHA-256
Dataset contract
quality evidence
report schema
source artifact linkage
```

V0.4 can then compare:

```text
previous Dataset
       ↕
current Dataset
```

and replay from stored RAW artifacts.

---

# 189. V0.4 must not leak into V0.3

Do NOT add in this release:

```text
dataset diff engine
replay CLI
version graph
snapshot registry
historical publication switch
```

Only ensure V0.3 evidence is suitable for those future capabilities.

---

# 190. Implementation guardrails

Every V0.3 PR should ask:

```text
Does this belong to HOW TO INGEST?

Does it preserve Dataset neutrality?

Does it mutate user data implicitly?

Does it create a dependency all users must pay for?

Does it prevent a future streaming implementation?

Is this framework infrastructure or business logic?
```

---

# 191. Code-review checklist

Reviewers should verify:

- public API additions are deliberate;
- dataclasses are immutable where they represent evidence/contracts;
- no accidental DataFrame dependency;
- new extras are lazy;
- errors are framework exceptions;
- no source data appears in logs unexpectedly;
- issue/report schemas are deterministic;
- tests are offline;
- backend libraries are hidden behind framework adapters.

---

# 192. Documentation checklist

Before stable release:

```text
README
CHANGELOG
ADR index
architecture index
Contracts V2 guide
profiling guide
quality report guide
NDJSON guide
Excel guide
Parquet guide
release validation guide
```

---

# 193. Example final user experience

```python
from pyingestkit import (
    DatasetContract,
    FieldContract,
    NdjsonParser,
)

from pyingestkit.profiling import DatasetProfiler

parser = NdjsonParser()
dataset = parser.parse(raw)

contract = DatasetContract(
    fields=(
        FieldContract(
            "postal_code",
            nullable=False,
            expected_type=str,
            pattern=r"[0-9]{5}",
        ),
        FieldContract(
            "commune",
            nullable=False,
            expected_type=str,
        ),
    ),
    primary_key=("postal_code", "commune"),
)

validation = contract.validate(dataset)
profile = DatasetProfiler().profile(dataset)
```

This remains ordinary Python.

---

# 194. Example Excel use

```python
from pyingestkit.parsers import ExcelParser

parser = ExcelParser(sheet_name="Codes postaux")
dataset = parser.parse(raw)
```

Installation:

```bash
pip install "pyingestkit[excel]"
```

---

# 195. Example Parquet use

```python
from pyingestkit.parsers import ParquetParser

parser = ParquetParser()
dataset = parser.parse(raw)
```

Installation:

```bash
pip install "pyingestkit[parquet]"
```

---

# 196. Example issue result

```json
{
  "rule": "field.pattern",
  "severity": "ERROR",
  "field": "postal_code",
  "row_index": 19,
  "message": "Field 'postal_code' does not match the declared pattern"
}
```

No full row dump.

---

# 197. Example profile result

```json
{
  "row_count": 3,
  "field_count": 2,
  "duplicate_row_count": 0,
  "fields": [
    {
      "name": "postal_code",
      "null_count": 0,
      "distinct_count": 3,
      "observed_types": ["str"],
      "min_length": 5,
      "max_length": 5
    }
  ]
}
```

---

# 198. Stable release quality bar

V0.3.0 should not be declared stable merely because parsers work.

Stable means:

```text
API deliberate
semantics documented
errors controlled
reports reproducible
extras isolated
security reviewed
CI green
wheel validated
reference jobs executable
```

---

# 199. Immediate implementation task

After this architecture document is accepted:

```text
git checkout -b feat/v0.3-quality-formats
```

Then implement only:

```text
V0.3.0-a1 — Quality Contracts V2
```

Initial files:

```text
src/pyingestkit/contracts/dataset.py
src/pyingestkit/validation/result.py
tests/unit/contracts/test_dataset_contract_v2.py
tests/contract/test_dataset_parser_public_api.py
docs/adr/ADR-028-dataset-contracts-v2-semantics.md
docs/guides/dataset-contracts-v2.md
```

No parser dependencies should enter the first alpha.

---

# 200. Release sequence summary

```text
V0.2.0
ACQUISITION RELEASE
        │
        ▼
V0.3.0-a1
QUALITY CONTRACTS V2
        │
        ▼
V0.3.0-a2
DATASET PROFILING + QUALITY REPORTS
        │
        ▼
V0.3.0-b1
NDJSON + EXCEL
        │
        ▼
V0.3.0-b2
PARQUET
        │
        ▼
V0.3.0-rc1
QUALITY & FORMATS E2E
        │
        ▼
V0.3.0
QUALITY & FORMATS RELEASE
```

This sequence intentionally separates validation semantics, profiling/evidence, new text/spreadsheet formats, and the heavier columnar backend so that each boundary can be reviewed before becoming stable.
