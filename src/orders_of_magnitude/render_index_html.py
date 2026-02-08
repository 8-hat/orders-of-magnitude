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
DATA_ROOT = ROOT / "data"
TEMPLATE_ROOT = PACKAGE_ROOT / "templates"
INDEX_PATH = ROOT / "index.html"
INDEX_CSS_PATH = ROOT / "index.css"
TABLES_PLACEHOLDER = "{{ tables }}"
DATASET_SOURCES: tuple[tuple[Path, str], ...] = (
    (DATA_ROOT / "lengths.yml", "m"),
    (DATA_ROOT / "times.yml", "s"),
)
UNIT_REGISTRY: pint.UnitRegistry[Any] = pint.UnitRegistry()


@dataclass(frozen=True)
class Observable:
    """Observable rendered in the index table."""

    name: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class Dataset:
    """Dataset and its normalized observables."""

    title: str
    observables: list[Observable]


def _read_text(path: Path, label: str) -> str:
    if not path.exists():
        msg = f"Missing {label} at {path}."
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def _parse_observable(item: object, index: int, target_unit: str) -> Observable:
    if not isinstance(item, dict):
        msg = f"Observable {index} must be a mapping."
        raise TypeError(msg)

    try:
        name_raw = item["name"]
        value_raw = item["value"]
        unit_raw = item["unit"]
    except KeyError as exc:
        missing_field = exc.args[0]
        msg = f"Observable {index} missing '{missing_field}'."
        raise ValueError(msg) from exc

    if not isinstance(name_raw, str):
        msg = f"Observable {index} field 'name' must be a string."
        raise TypeError(msg)
    if not isinstance(unit_raw, str):
        msg = f"Observable {index} field 'unit' must be a string."
        raise TypeError(msg)
    if isinstance(value_raw, bool) or not isinstance(value_raw, (int, float, str)):
        msg = f"Observable {index} field 'value' must be a number."
        raise TypeError(msg)

    value, unit = _convert_to_target_unit(
        Decimal(str(value_raw)), unit_raw, target_unit, index
    )
    return Observable(name=name_raw, value=value, unit=unit)


def _convert_to_target_unit(
    value: Decimal, unit: str, target_unit: str, index: int
) -> tuple[Decimal, str]:
    try:
        quantity = value * UNIT_REGISTRY(unit)
    except pint_errors.UndefinedUnitError as exc:
        msg = f"Observable {index} field 'unit' has unsupported unit '{unit}'."
        raise ValueError(msg) from exc

    try:
        magnitude = quantity.to(target_unit).magnitude
    except pint_errors.DimensionalityError as exc:
        msg = (
            f"Observable {index} field 'unit' ('{unit}') cannot convert to "
            f"{target_unit}."
        )
        raise ValueError(msg) from exc

    return Decimal(str(magnitude)), target_unit


def _scientific_parts(value: Decimal) -> tuple[str, int]:
    if value.is_zero():
        return "0.00", 0
    if not value.is_finite():
        msg = "Observable value must be a finite number."
        raise ValueError(msg)

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
    raw = yaml.safe_load(_read_text(path, "YAML file"))
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

    observables = [
        _parse_observable(item, index, target_unit) for index, item in enumerate(items)
    ]

    return Dataset(title=title, observables=observables)


def _render_row(observable: Observable, indent: str) -> str:
    mantissa, exponent = _scientific_parts(observable.value)
    unit = html.escape(observable.unit)
    name = html.escape(observable.name)
    order = f"10<sup>{exponent}</sup> {unit}"
    value = f"{mantissa} x 10<sup>{exponent}</sup> {unit}"
    return (
        f"{indent}<tr>\n"
        f'{indent}  <td class="math">{order}</td>\n'
        f"{indent}  <td>{name}</td>\n"
        f'{indent}  <td class="math">{value}</td>\n'
        f"{indent}</tr>"
    )


def _render_table(dataset: Dataset, indent: str) -> str:
    rows = "\n".join(
        _render_row(observable, f"{indent}      ") for observable in dataset.observables
    )
    return (
        f'{indent}<section class="dataset">\n'
        f"{indent}  <h2>{html.escape(dataset.title)}</h2>\n"
        f"{indent}  <table>\n"
        f"{indent}    <thead>\n"
        f"{indent}      <tr>\n"
        f"{indent}        <th>Order of magnitude</th>\n"
        f"{indent}        <th>Name</th>\n"
        f"{indent}        <th>Value</th>\n"
        f"{indent}      </tr>\n"
        f"{indent}    </thead>\n"
        f"{indent}    <tbody>\n"
        f"{rows}\n"
        f"{indent}    </tbody>\n"
        f"{indent}  </table>\n"
        f"{indent}</section>"
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
        msg = f"Template missing tables placeholder '{TABLES_PLACEHOLDER}'."
        raise ValueError(msg)

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
    _render_index_html(INDEX_PATH, TEMPLATE_ROOT / "index.html", datasets)
    _render_index_css(INDEX_CSS_PATH, TEMPLATE_ROOT / "index.css")


if __name__ == "__main__":
    main()
