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
OBSERVABLE_REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "value",
    "unit",
    "fields",
    "source",
)
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


def _ensure_string(value: object, label: str) -> str:
    """Validate that ``value`` is a string and return it."""
    if isinstance(value, str):
        return value
    message = f"{label} must be a string."
    raise TypeError(message)


def _parse_number(value: object, label: str) -> float:
    """Convert a numeric-like value to ``float`` while rejecting booleans."""
    message = f"{label} must be a number."
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(message)
    try:
        return float(value)
    except ValueError as exc:
        raise TypeError(message) from exc


def _required_observable_fields(
    observable: dict[str, object], index: int
) -> dict[str, object]:
    """Return required observable values or raise a field-specific error."""
    fields = {}
    for field in OBSERVABLE_REQUIRED_FIELDS:
        if field not in observable:
            message = f"Observable {index} missing '{field}'."
            raise ValueError(message)
        fields[field] = observable[field]
    return fields


def _field_label(index: int, field: str) -> str:
    """Return the human-readable label used in validation errors."""
    return f"Observable {index} field '{field}'"


def _parse_observable(item: object, index: int, target_unit: str) -> Observable:
    """Parse one observable mapping, validate required fields, and normalize units."""
    observable = _ensure_mapping(item, f"Observable {index} must be a mapping.")
    fields = _required_observable_fields(observable, index)

    name = _ensure_string(fields["name"], _field_label(index, "name"))
    unit = _ensure_string(fields["unit"], _field_label(index, "unit"))
    observable_fields = _ensure_string(fields["fields"], _field_label(index, "fields"))
    source = _ensure_string(fields["source"], _field_label(index, "source"))
    value = _parse_number(fields["value"], _field_label(index, "value"))

    value = _convert_to_target_unit(value, unit, target_unit, index)
    return Observable(
        name=name,
        fields=observable_fields,
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
    title = _ensure_string(raw.get("title"), "YAML 'title'")
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
