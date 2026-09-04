from __future__ import annotations

from pyingestkit import Dataset, DatasetContract, ExcelParser, FieldContract, RunContext, job, step
from pyingestkit.artifacts import RawArtifact

from .quality_common import excel_fixture_bytes, fixture_raw, profiled_payload, validated_payload

CONTRACT = DatasetContract(
    fields=(
        FieldContract("id", nullable=False, expected_type=int, unique=True, min_value=1),
        FieldContract("name", nullable=False, expected_type=str, min_length=1),
        FieldContract(
            "score",
            nullable=False,
            expected_type=(int, float),
            min_value=0,
            max_value=100,
        ),
    ),
    allow_extra_fields=False,
    min_rows=1,
    primary_key=("id",),
)


@step(name="FetchExcelFixture")
def fetch_excel(context: RunContext) -> RawArtifact:
    return fixture_raw(
        context,
        name="people.xlsx",
        data=excel_fixture_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@step(name="ParseExcel")
def parse_excel(data: RawArtifact) -> Dataset:
    return ExcelParser(sheet="People").parse(data)


@step(name="ValidateExcelDataset")
def validate_excel(data: Dataset) -> dict[str, object]:
    return validated_payload(data, CONTRACT)


@step(name="ProfileExcelDataset")
def profile_excel(data: dict[str, object]) -> dict[str, object]:
    return profiled_payload(data)


@job(
    id="demo.excel_quality",
    version="0.4.0b2",
    description="Reference XLSX -> Dataset -> Contract V2 -> profile -> quality reports slice.",
)
def excel_quality_job() -> None:
    fetch_excel()
    parse_excel()
    validate_excel()
    profile_excel()


job_definition = excel_quality_job
