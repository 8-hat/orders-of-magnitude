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
PACKAGE_ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.html"
INDEX_CSS_PATH = ROOT / "index.css"
HTML_TEMPLATE_PATH = PACKAGE_ROOT / "templates" / "index.html"
CSS_TEMPLATE_PATH = PACKAGE_ROOT / "templates" / "index.css"
TABLES_PLACEHOLDER = "{{ tables }}"
UNIT_REGISTRY: pint.UnitRegistry[Any] = pint.UnitRegistry()


@dataclass(frozen=True)
class Observable:
    """Structured observable used to render the index table."""

    name: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class Dataset:
    """Structured dataset used to render the index table."""

    title: str
    observables: list[Observable]


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration for a dataset source and its target unit."""

    path: Path
    target_unit: str


DATASET_CONFIGS: tuple[DatasetConfig, ...] = (
    DatasetConfig(path=ROOT / "data" / "lengths.yml", target_unit="m"),
    DatasetConfig(path=ROOT / "data" / "times.yml", target_unit="s"),
)


def _require_field(item: dict[str, object], field: str, index: int) -> object:
    if field not in item:
        msg = f"Observable {index} missing '{field}'."
        raise ValueError(msg)
    return item[field]


def _parse_decimal(value: object, field: str, index: int) -> Decimal:
    if isinstance(value, bool):
        msg = f"Observable {index} field '{field}' must be a number."
        raise TypeError(msg)
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    msg = f"Observable {index} field '{field}' must be a number."
    raise TypeError(msg)


def _parse_str(value: object, field: str, index: int) -> str:
    if isinstance(value, str):
        return value
    msg = f"Observable {index} field '{field}' must be a string."
    raise TypeError(msg)


def _convert_to_target_unit(
    value: Decimal, unit: str, target_unit: str, index: int
) -> tuple[Decimal, str]:
    try:
        quantity = value * UNIT_REGISTRY(unit)
    except pint_errors.UndefinedUnitError as exc:
        msg = f"Observable {index} field 'unit' has unsupported unit '{unit}'."
        raise ValueError(msg) from exc

    try:
        converted = quantity.to(target_unit)
    except pint_errors.DimensionalityError as exc:
        msg = (
            f"Observable {index} field 'unit' ('{unit}') cannot convert to "
            f"{target_unit}."
        )
        raise ValueError(msg) from exc

    magnitude = converted.magnitude
    if not isinstance(magnitude, Decimal):
        magnitude = Decimal(str(magnitude))
    return magnitude, target_unit


def _scientific_parts(value: Decimal) -> tuple[str, int]:
    if value.is_zero():
        return "0.00", 0
    if not value.is_finite():
        msg = "Observable value must be a finite number."
        raise ValueError(msg)

    sign = "-" if value.is_signed() else ""
    magnitude = value.copy_abs()
    exponent = magnitude.adjusted()
    mantissa = magnitude.scaleb(-exponent)

    mantissa = mantissa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if mantissa == Decimal("10.00"):
        mantissa = Decimal("1.00")
        exponent += 1

    mantissa_str = f"{sign}{mantissa}"
    return mantissa_str, exponent


def _load_dataset(config: DatasetConfig) -> Dataset:
    path = config.path
    if not path.exists():
        msg = f"Missing YAML file at {path}."
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "Top-level YAML must be a mapping with an 'observables' key."
        raise TypeError(msg)

    title = raw.get("title")
    if not isinstance(title, str):
        msg = "YAML 'title' must be a string."
        raise TypeError(msg)

    items = raw.get("observables")
    if not isinstance(items, list):
        msg = "YAML 'observables' must be a list."
        raise TypeError(msg)

    observables: list[Observable] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            msg = f"Observable {index} must be a mapping."
            raise TypeError(msg)

        name = _parse_str(_require_field(item, "name", index), "name", index)
        value = _parse_decimal(
            _require_field(item, "value", index),
            "value",
            index,
        )
        unit = _parse_str(_require_field(item, "unit", index), "unit", index)
        value, unit = _convert_to_target_unit(value, unit, config.target_unit, index)

        observables.append(
            Observable(
                name=name,
                value=value,
                unit=unit,
            )
        )

    return Dataset(title=title, observables=observables)


def _render_rows(observables: list[Observable], indent: str) -> str:
    indent_tr = f"{indent}  "
    indent_td = f"{indent_tr}  "

    rows: list[str] = []
    for observable in observables:
        mantissa, exponent = _scientific_parts(observable.value)
        unit = html.escape(observable.unit)
        name = html.escape(observable.name)
        order = f"10<sup>{exponent}</sup> {unit}"
        value = f"{mantissa} x 10<sup>{exponent}</sup> {unit}"
        row = "\n".join(
            [
                f"{indent_tr}<tr>",
                f'{indent_td}<td class="math">{order}</td>',
                f"{indent_td}<td>{name}</td>",
                f'{indent_td}<td class="math">{value}</td>',
                f"{indent_tr}</tr>",
            ]
        )
        rows.append(row)

    return "\n".join(rows)


def _render_table(dataset: Dataset, indent: str) -> str:
    title = html.escape(dataset.title)
    tbody_indent = f"{indent}    "
    rows_html = _render_rows(dataset.observables, tbody_indent)
    table_lines = [
        f'{indent}<section class="dataset">',
        f"{indent}  <h2>{title}</h2>",
        f"{indent}  <table>",
        f"{indent}    <thead>",
        f"{indent}      <tr>",
        f"{indent}        <th>Order of magnitude</th>",
        f"{indent}        <th>Name</th>",
        f"{indent}        <th>Value</th>",
        f"{indent}      </tr>",
        f"{indent}    </thead>",
        f"{indent}    <tbody>",
        rows_html,
        f"{indent}    </tbody>",
        f"{indent}  </table>",
        f"{indent}</section>",
    ]
    return "\n".join(table_lines)


def _render_tables(datasets: list[Dataset], indent: str) -> str:
    return "\n\n".join(_render_table(dataset, indent) for dataset in datasets)


def _render_index_html(
    index_path: Path, template_path: Path, datasets: list[Dataset]
) -> None:
    if not template_path.exists():
        msg = f"Missing HTML template at {template_path}."
        raise FileNotFoundError(msg)

    template_text = template_path.read_text(encoding="utf-8")
    if TABLES_PLACEHOLDER not in template_text:
        msg = f"Template missing tables placeholder '{TABLES_PLACEHOLDER}'."
        raise ValueError(msg)

    placeholder_line = next(
        (line for line in template_text.splitlines() if TABLES_PLACEHOLDER in line),
        None,
    )
    if placeholder_line is None:
        msg = f"Template missing tables placeholder '{TABLES_PLACEHOLDER}'."
        raise ValueError(msg)

    indent = placeholder_line.split(TABLES_PLACEHOLDER, 1)[0]
    tables_html = _render_tables(datasets, indent)
    rendered = template_text.replace(placeholder_line, tables_html, 1)
    index_path.write_text(rendered, encoding="utf-8")


def _render_index_css(index_css_path: Path, template_css_path: Path) -> None:
    if not template_css_path.exists():
        msg = f"Missing CSS template at {template_css_path}."
        raise FileNotFoundError(msg)

    css_text = template_css_path.read_text(encoding="utf-8")
    index_css_path.write_text(css_text, encoding="utf-8")


def main() -> None:
    datasets = [_load_dataset(config) for config in DATASET_CONFIGS]
    _render_index_html(INDEX_PATH, HTML_TEMPLATE_PATH, datasets)
    _render_index_css(INDEX_CSS_PATH, CSS_TEMPLATE_PATH)


if __name__ == "__main__":
    main()
