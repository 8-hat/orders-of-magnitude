"""Load and normalize observable datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pint
import yaml
from pint import errors as pint_errors

PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PACKAGE_ROOT / "data"
DATASET_SOURCES: tuple[tuple[Path, str], ...] = (
    (DATA_ROOT / "lengths.yml", "m"),
    (DATA_ROOT / "times.yml", "s"),
)
UNIT_REGISTRY: pint.UnitRegistry[Any] = pint.UnitRegistry()


@dataclass(frozen=True)
class Observable:
    """Single observable entry normalized to the dataset target unit."""

    name: str
    fields: str
    source: str
    value: float
    unit: str


@dataclass(frozen=True)
class Dataset:
    """Collection of observables sharing a target unit."""

    title: str
    observables: list[Observable]


def _read_text(path: Path, label: str) -> str:
    """Return UTF-8 text from ``path`` or raise if the file is missing."""
    if not path.exists():
        message = f"Missing {label} at {path}."
        raise FileNotFoundError(message)
    return path.read_text(encoding="utf-8")


def _ensure_mapping(item: object, message: str) -> dict[str, object]:
    """Validate that ``item`` is a YAML mapping and return it."""
    if isinstance(item, dict):
        return item
    raise TypeError(message)


def _observable_field(observable: dict[str, object], index: int, field: str) -> object:
    """Return one required observable value or raise a field-specific error."""
    if field in observable:
        return observable[field]
    message = f"Observable {index} missing '{field}'."
    raise ValueError(message)


def _observable_string(observable: dict[str, object], index: int, field: str) -> str:
    """Return one required observable field as a string."""
    value = _observable_field(observable, index, field)
    label = f"Observable {index} field '{field}'"
    if isinstance(value, str):
        return value
    message = f"{label} must be a string."
    raise TypeError(message)


def _observable_number(observable: dict[str, object], index: int, field: str) -> float:
    """Return one required observable field as a float."""
    value = _observable_field(observable, index, field)
    label = f"Observable {index} field '{field}'"
    message = f"{label} must be a number."
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(message)
    try:
        return float(value)
    except ValueError as exc:
        raise TypeError(message) from exc


def _parse_observable(item: object, index: int, target_unit: str) -> Observable:
    """Parse one observable mapping, validate required fields, and normalize units."""
    observable = _ensure_mapping(item, f"Observable {index} must be a mapping.")
    name = _observable_string(observable, index, "name")
    unit = _observable_string(observable, index, "unit")
    fields = _observable_string(observable, index, "fields")
    source = _observable_string(observable, index, "source")
    value = _observable_number(observable, index, "value")

    value = _convert_to_target_unit(value, unit, target_unit, index)
    return Observable(
        name=name,
        fields=fields,
        source=source,
        value=value,
        unit=target_unit,
    )


def _convert_to_target_unit(
    value: float, unit: str, target_unit: str, index: int
) -> float:
    """Convert ``value`` from ``unit`` to ``target_unit`` and return a ``float``."""
    try:
        quantity = value * UNIT_REGISTRY(unit)
    except pint_errors.UndefinedUnitError as exc:
        message = f"Observable {index} field 'unit' has unsupported unit '{unit}'."
        raise ValueError(message) from exc

    try:
        magnitude = quantity.to(target_unit).magnitude
    except pint_errors.DimensionalityError as exc:
        message = (
            f"Observable {index} field 'unit' ('{unit}') cannot convert to "
            f"{target_unit}."
        )
        raise ValueError(message) from exc

    return float(magnitude)


def load_dataset(path: Path, target_unit: str) -> Dataset:
    """Load and validate a dataset YAML file, converting all values to one unit."""
    raw = _ensure_mapping(
        yaml.safe_load(_read_text(path, "YAML file")),
        "Top-level YAML must be a mapping with an 'observables' key.",
    )
    title = raw.get("title")
    if not isinstance(title, str):
        message = "YAML 'title' must be a string."
        raise TypeError(message)

    items = raw.get("observables")
    if not isinstance(items, list):
        message = "YAML 'observables' must be a list."
        raise TypeError(message)

    observables = sorted(
        (
            _parse_observable(item, index, target_unit)
            for index, item in enumerate(items)
        ),
        key=lambda observable: observable.value,
    )
    return Dataset(title=title, observables=observables)


def load_datasets() -> list[Dataset]:
    """Load every configured dataset source."""
    return [load_dataset(path, target) for path, target in DATASET_SOURCES]
