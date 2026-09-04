from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from pyingestkit.core.exceptions import DiffError
from pyingestkit.dataset import Dataset
from pyingestkit.diff.models import DatasetDiff, DiffEntry, DiffKind, DiffPolicy, SchemaDiff
from pyingestkit.versioning import DatasetFingerprinter, DatasetFingerprintPolicy
from pyingestkit.versioning._canonical import MISSING, canonical_json, canonical_value


class DatasetDiffer:
    def __init__(self, policy: DiffPolicy | None = None) -> None:
        self.policy = policy or DiffPolicy()

    def compare(self, previous: Dataset, candidate: Dataset) -> DatasetDiff:
        schema = self._schema_diff(previous, candidate)
        fingerprinter = DatasetFingerprinter(
            DatasetFingerprintPolicy(order_sensitive=self.policy.order_sensitive)
        )
        previous_fingerprint = fingerprinter.fingerprint(previous)
        candidate_fingerprint = fingerprinter.fingerprint(candidate)

        if self.policy.key_fields:
            counts, entries = self._compare_keyed(previous, candidate)
        else:
            counts, entries = self._compare_keyless(previous, candidate)

        limit = self.policy.max_entries
        entries_truncated = limit is not None and len(entries) > limit
        bounded_entries = entries if limit is None else entries[:limit]
        added, removed, changed, unchanged = counts
        return DatasetDiff(
            previous_fingerprint=previous_fingerprint,
            candidate_fingerprint=candidate_fingerprint,
            policy=self.policy,
            schema=schema,
            added_count=added,
            removed_count=removed,
            changed_count=changed,
            unchanged_count=unchanged,
            entries=tuple(bounded_entries),
            entries_truncated=entries_truncated,
        )

    @staticmethod
    def _schema_diff(previous: Dataset, candidate: Dataset) -> SchemaDiff:
        previous_set = set(previous.fields)
        candidate_set = set(candidate.fields)
        common_previous = tuple(field for field in previous.fields if field in candidate_set)
        common_candidate = tuple(field for field in candidate.fields if field in previous_set)
        return SchemaDiff(
            added_fields=tuple(field for field in candidate.fields if field not in previous_set),
            removed_fields=tuple(field for field in previous.fields if field not in candidate_set),
            common_fields=common_previous,
            field_order_changed=common_previous != common_candidate,
        )

    def _compare_keyed(
        self, previous: Dataset, candidate: Dataset
    ) -> tuple[tuple[int, int, int, int], list[DiffEntry]]:
        self._validate_policy_fields(previous, candidate)
        previous_index = self._key_index(previous, "previous")
        candidate_index = self._key_index(candidate, "candidate")
        previous_keys = set(previous_index)
        candidate_keys = set(candidate_index)
        added_keys = candidate_keys - previous_keys
        removed_keys = previous_keys - candidate_keys
        common_keys = previous_keys.intersection(candidate_keys)
        compare_fields = self._comparison_fields(previous, candidate)

        entries: list[tuple[str, DiffEntry]] = []
        for token in added_keys:
            key, row = candidate_index[token]
            entries.append(
                (
                    f"0:{token}",
                    DiffEntry(
                        DiffKind.ADDED,
                        key=key,
                        after=row if self.policy.capture_values else None,
                    ),
                )
            )
        for token in removed_keys:
            key, row = previous_index[token]
            entries.append(
                (
                    f"1:{token}",
                    DiffEntry(
                        DiffKind.REMOVED,
                        key=key,
                        before=row if self.policy.capture_values else None,
                    ),
                )
            )

        changed_count = 0
        unchanged_count = 0
        for token in common_keys:
            key, before = previous_index[token]
            _, after = candidate_index[token]
            changed_fields = tuple(
                field
                for field in compare_fields
                if self._field_token(before, field) != self._field_token(after, field)
            )
            if changed_fields:
                changed_count += 1
                entries.append(
                    (
                        f"2:{token}",
                        DiffEntry(
                            DiffKind.CHANGED,
                            key=key,
                            changed_fields=changed_fields,
                            before=before if self.policy.capture_values else None,
                            after=after if self.policy.capture_values else None,
                        ),
                    )
                )
            else:
                unchanged_count += 1
        entries.sort(key=lambda item: item[0])
        return (
            (len(added_keys), len(removed_keys), changed_count, unchanged_count),
            [entry for _, entry in entries],
        )

    def _compare_keyless(
        self, previous: Dataset, candidate: Dataset
    ) -> tuple[tuple[int, int, int, int], list[DiffEntry]]:
        fields = self._comparison_fields(previous, candidate, keyless=True)
        previous_rows = self._row_multiset(previous, fields)
        candidate_rows = self._row_multiset(candidate, fields)
        previous_counts = Counter(token for token, _ in previous_rows)
        candidate_counts = Counter(token for token, _ in candidate_rows)
        added_counter = candidate_counts - previous_counts
        removed_counter = previous_counts - candidate_counts
        unchanged_count = sum((previous_counts & candidate_counts).values())
        previous_samples = {token: row for token, row in previous_rows}
        candidate_samples = {token: row for token, row in candidate_rows}
        entries: list[tuple[str, DiffEntry]] = []
        for token in sorted(added_counter):
            for index in range(added_counter[token]):
                entries.append(
                    (
                        f"0:{token}:{index:020d}",
                        DiffEntry(
                            DiffKind.ADDED,
                            after=(
                                candidate_samples[token] if self.policy.capture_values else None
                            ),
                        ),
                    )
                )
        for token in sorted(removed_counter):
            for index in range(removed_counter[token]):
                entries.append(
                    (
                        f"1:{token}:{index:020d}",
                        DiffEntry(
                            DiffKind.REMOVED,
                            before=(
                                previous_samples[token] if self.policy.capture_values else None
                            ),
                        ),
                    )
                )
        entries.sort(key=lambda item: item[0])
        return (
            (sum(added_counter.values()), sum(removed_counter.values()), 0, unchanged_count),
            [entry for _, entry in entries],
        )

    def _validate_policy_fields(self, previous: Dataset, candidate: Dataset) -> None:
        for field in self.policy.key_fields:
            if field not in previous.fields or field not in candidate.fields:
                raise DiffError(f"Key field {field!r} must exist in both dataset schemas")
        if self.policy.compare_fields is not None:
            for field in self.policy.compare_fields:
                if field not in previous.fields or field not in candidate.fields:
                    raise DiffError(f"Compare field {field!r} must exist in both dataset schemas")

    def _key_index(
        self, dataset: Dataset, label: str
    ) -> dict[str, tuple[tuple[Any, ...], Mapping[str, Any]]]:
        index: dict[str, tuple[tuple[Any, ...], Mapping[str, Any]]] = {}
        for row_index, row in enumerate(dataset):
            values: list[Any] = []
            for field in self.policy.key_fields:
                if field not in row:
                    raise DiffError(
                        f"{label} dataset row {row_index} is missing key field {field!r}"
                    )
                value = row[field]
                if value is None:
                    raise DiffError(
                        f"{label} dataset row {row_index} has null key field {field!r}"
                    )
                values.append(value)
            key = tuple(values)
            token = canonical_json(canonical_value(key))
            if token in index:
                raise DiffError(
                    f"{label} dataset contains duplicate key at row {row_index}: "
                    f"fields={self.policy.key_fields!r}"
                )
            index[token] = (key, row)
        return index

    def _comparison_fields(
        self, previous: Dataset, candidate: Dataset, *, keyless: bool = False
    ) -> tuple[str, ...]:
        if self.policy.compare_fields is not None:
            if keyless:
                self._validate_policy_fields(previous, candidate)
            return self.policy.compare_fields
        fields = list(previous.fields)
        fields.extend(field for field in candidate.fields if field not in fields)
        excluded = set(self.policy.ignore_fields)
        if not keyless:
            excluded.update(self.policy.key_fields)
        return tuple(field for field in fields if field not in excluded)

    @staticmethod
    def _field_token(row: Mapping[str, Any], field: str) -> str:
        return canonical_json(canonical_value(row[field] if field in row else MISSING))

    def _row_multiset(
        self, dataset: Dataset, fields: Sequence[str]
    ) -> list[tuple[str, Mapping[str, Any]]]:
        result: list[tuple[str, Mapping[str, Any]]] = []
        for row in dataset:
            encoded = {
                "$type": "diff-row",
                "fields": [
                    [field, canonical_value(row[field] if field in row else MISSING)]
                    for field in fields
                ],
            }
            result.append((canonical_json(encoded), row))
        return result
