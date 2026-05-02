from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from orders_of_magnitude import datasets

if TYPE_CHECKING:
    from pathlib import Path


def test_load_dataset_requires_fields_key(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    dataset_path.write_text(
        "title: Demo\nobservables:\n  - name: Example\n    value: 1\n    unit: m\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Observable 0 missing 'fields'\."):
        datasets.load_dataset(dataset_path, "m")


def test_load_dataset_requires_source_key(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    dataset_path.write_text(
        "title: Demo\n"
        "observables:\n"
        "  - name: Example\n"
        "    value: 1\n"
        "    unit: m\n"
        "    fields: test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Observable 0 missing 'source'\."):
        datasets.load_dataset(dataset_path, "m")


def test_load_dataset_sorts_observables_by_normalized_value(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    dataset_path.write_text(
        "title: Demo\n"
        "observables:\n"
        "  - name: larger\n"
        "    value: 100\n"
        "    unit: cm\n"
        "    fields: test\n"
        "    source: source\n"
        "  - name: smaller\n"
        "    value: 1\n"
        "    unit: mm\n"
        "    fields: test\n"
        "    source: source\n"
        "  - name: middle\n"
        "    value: 2\n"
        "    unit: cm\n"
        "    fields: test\n"
        "    source: source\n",
        encoding="utf-8",
    )

    dataset = datasets.load_dataset(dataset_path, "m")

    assert [observable.name for observable in dataset.observables] == [
        "smaller",
        "middle",
        "larger",
    ]
    assert [observable.value for observable in dataset.observables] == [
        0.001,
        0.02,
        1.0,
    ]
