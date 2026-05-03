from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from orders_of_magnitude import datasets

if TYPE_CHECKING:
    from pathlib import Path


def _write_dataset(path: Path, observables: list[dict[str, object]]) -> None:
    path.write_text(
        yaml.safe_dump(
            {"title": "Demo", "observables": observables},
            sort_keys=False,
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("field", ["fields", "source"])
def test_load_dataset_requires_observable_fields(tmp_path: Path, field: str) -> None:
    dataset_path = tmp_path / "dataset.yml"
    observable: dict[str, object] = {
        "name": "Example",
        "value": 1,
        "unit": "m",
        "fields": "test",
        "source": "source",
    }
    del observable[field]
    _write_dataset(dataset_path, [observable])

    with pytest.raises(ValueError, match=rf"Observable 0 missing '{field}'\."):
        datasets.load_dataset(dataset_path, "m")


def test_load_dataset_sorts_observables_by_normalized_value(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    _write_dataset(
        dataset_path,
        [
            {
                "name": "larger",
                "value": 100,
                "unit": "cm",
                "fields": "test",
                "source": "source",
            },
            {
                "name": "smaller",
                "value": 1,
                "unit": "mm",
                "fields": "test",
                "source": "source",
            },
            {
                "name": "middle",
                "value": 2,
                "unit": "cm",
                "fields": "test",
                "source": "source",
            },
        ],
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
