"""Render index.html and index.css from dataset YAML files and templates."""

from __future__ import annotations

import html
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pint
import yaml
from pint import errors as pint_errors

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"
HTML_TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"
CSS_TEMPLATE_PATH = HTML_TEMPLATE_ROOT / "index.css"
INDEX_PATH = ROOT / "index.html"
INDEX_CSS_PATH = ROOT / "index.css"
TABLES_PLACEHOLDER = "{{ tables }}"
TABLE_HEADERS: tuple[str, ...] = ("Order of magnitude", "Name", "Value")
DATASET_SOURCES: tuple[tuple[Path, str], ...] = (
    (DATA_ROOT / "lengths.yml", "m"),
    (DATA_ROOT / "times.yml", "s"),
)
UNIT_REGISTRY: pint.UnitRegistry[Any] = pint.UnitRegistry()


@dataclass(frozen=True)
class Observable:
    """Single observable entry normalized to the dataset target unit."""

    name: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class Dataset:
    """Collection of observables rendered as one section in the index page."""

    title: str
    observables: list[Observable]


def _read_text(path: Path, label: str) -> str:
    if not path.exists():
        message = f"Missing {label} at {path}."
        raise FileNotFoundError(message)
    return path.read_text(encoding="utf-8")


def _as_mapping(item: object, message: str) -> dict[str, object]:
    if isinstance(item, dict):
        return item
    raise TypeError(message)


def _parse_observable(item: object, index: int, target_unit: str) -> Observable:
    observable = _as_mapping(item, f"Observable {index} must be a mapping.")
    for field in ("name", "value", "unit"):
        if field not in observable:
            message = f"Observable {index} missing '{field}'."
            raise ValueError(message)

    name_raw = observable["name"]
    value_raw = observable["value"]
    unit_raw = observable["unit"]
    if not isinstance(name_raw, str):
        message = f"Observable {index} field 'name' must be a string."
        raise TypeError(message)
    if not isinstance(unit_raw, str):
        message = f"Observable {index} field 'unit' must be a string."
        raise TypeError(message)
    if isinstance(value_raw, bool) or not isinstance(value_raw, (int, float, str)):
        message = f"Observable {index} field 'value' must be a number."
        raise TypeError(message)

    value = _convert_to_target_unit(
        Decimal(str(value_raw)), unit_raw, target_unit, index
    )
    return Observable(name=name_raw, value=value, unit=target_unit)


def _convert_to_target_unit(
    value: Decimal, unit: str, target_unit: str, index: int
) -> Decimal:
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

    return Decimal(str(magnitude))


def _scientific_parts(value: Decimal) -> tuple[str, int]:
    if value.is_zero():
        return "0.00", 0
    if not value.is_finite():
        message = "Observable value must be a finite number."
        raise ValueError(message)

    exponent = value.copy_abs().adjusted()
    mantissa = (
        value.copy_abs()
        .scaleb(-exponent)
        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )
    if mantissa == Decimal("10.00"):
        mantissa = Decimal("1.00")
        exponent += 1
    sign = "-" if value.is_signed() else ""
    return f"{sign}{mantissa}", exponent


def _load_dataset(path: Path, target_unit: str) -> Dataset:
    raw = _as_mapping(
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

    observables = [
        _parse_observable(item, index, target_unit) for index, item in enumerate(items)
    ]
    return Dataset(title=title, observables=observables)


def _render_row(observable: Observable, indent: str) -> str:
    mantissa, exponent = _scientific_parts(observable.value)
    unit = html.escape(observable.unit)
    value = f"{mantissa} x 10<sup>{exponent}</sup> {unit}"
    return "\n".join(
        (
            f"{indent}<tr>",
            f'{indent}  <td class="math">10<sup>{exponent}</sup> {unit}</td>',
            f"{indent}  <td>{html.escape(observable.name)}</td>",
            f'{indent}  <td class="math">{value}</td>',
            f"{indent}</tr>",
        )
    )


def _render_table(dataset: Dataset, indent: str) -> str:
    row_indent = f"{indent}      "
    rows = "\n".join(
        _render_row(observable, row_indent) for observable in dataset.observables
    )
    headers = "\n".join(f"{indent}        <th>{label}</th>" for label in TABLE_HEADERS)
    return "\n".join(
        (
            f'{indent}<section class="dataset">',
            f"{indent}  <h2>{html.escape(dataset.title)}</h2>",
            f"{indent}  <table>",
            f"{indent}    <thead>",
            f"{indent}      <tr>",
            headers,
            f"{indent}      </tr>",
            f"{indent}    </thead>",
            f"{indent}    <tbody>",
            rows,
            f"{indent}    </tbody>",
            f"{indent}  </table>",
            f"{indent}</section>",
        )
    )


def _render_index_html(
    index_path: Path, template_path: Path, datasets: list[Dataset]
) -> None:
    template_text = _read_text(template_path, "HTML template")
    placeholder_line = next(
        (line for line in template_text.splitlines() if TABLES_PLACEHOLDER in line),
        None,
    )
    if placeholder_line is None:
        message = f"Template missing tables placeholder '{TABLES_PLACEHOLDER}'."
        raise ValueError(message)

    indent = placeholder_line.split(TABLES_PLACEHOLDER, 1)[0]
    tables_html = "\n\n".join(_render_table(dataset, indent) for dataset in datasets)
    index_path.write_text(
        template_text.replace(placeholder_line, tables_html, 1), encoding="utf-8"
    )


def _render_index_css(index_css_path: Path, template_css_path: Path) -> None:
    index_css_path.write_text(
        _read_text(template_css_path, "CSS template"), encoding="utf-8"
    )


def main() -> None:
    datasets = [_load_dataset(path, target) for path, target in DATASET_SOURCES]
    _render_index_html(INDEX_PATH, HTML_TEMPLATE_ROOT / "index.html", datasets)
    _render_index_css(INDEX_CSS_PATH, CSS_TEMPLATE_PATH)


if __name__ == "__main__":
    main()
