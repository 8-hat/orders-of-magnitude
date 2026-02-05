"""Render index.html from data/lengths.yml and data/times.yml."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pint
import yaml
from pint import errors as pint_errors

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "index.html"
STYLESHEET_HREF = "index.css"
TABLES_START = "<!-- DATA_TABLES_START -->"
TABLES_END = "<!-- DATA_TABLES_END -->"
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


def _ensure_stylesheet_link(html_text: str) -> str:
    link_pattern = (
        r"<link\b"
        r"(?=[^>]*\brel=[\"']stylesheet[\"'])"
        rf"(?=[^>]*\bhref=[\"']{re.escape(STYLESHEET_HREF)}[\"'])"
        r"[^>]*>"
    )
    if re.search(link_pattern, html_text, flags=re.IGNORECASE):
        return html_text

    head_open = re.search(r"(^\s*)<head>\s*$", html_text, flags=re.MULTILINE)
    if head_open is None:
        msg = "Could not find <head> tag in index.html."
        raise ValueError(msg)

    head_close = re.search(r"(^\s*</head>\s*$)", html_text, flags=re.MULTILINE)
    if head_close is None:
        msg = "Could not find </head> tag in index.html."
        raise ValueError(msg)

    indent = f"{head_open.group(1)}  "
    link_line = f'{indent}<link rel="stylesheet" href="{STYLESHEET_HREF}" />'
    insertion = f"{link_line}\n"
    return html_text[: head_close.start()] + insertion + html_text[head_close.start() :]


def _replace_tables(html_text: str, datasets: list[Dataset]) -> str:
    block_match = re.search(
        rf"(^\s*{re.escape(TABLES_START)}\s*$)(.*?)(^\s*{re.escape(TABLES_END)}\s*$)",
        html_text,
        flags=re.DOTALL | re.MULTILINE,
    )
    if block_match is None:
        msg = "Could not find data tables markers in index.html."
        raise ValueError(msg)

    indent_match = re.match(r"^(\s*)", block_match.group(1))
    indent = indent_match.group(1) if indent_match else ""
    tables_html = _render_tables(datasets, indent)
    new_block = f"{block_match.group(1)}\n{tables_html}\n{block_match.group(3)}"
    return html_text[: block_match.start()] + new_block + html_text[block_match.end() :]


def _render_index_html(index_path: Path, datasets: list[Dataset]) -> None:
    html_text = index_path.read_text(encoding="utf-8")
    html_text = _ensure_stylesheet_link(html_text)
    html_text = _replace_tables(html_text, datasets)
    index_path.write_text(html_text, encoding="utf-8")


def main() -> None:
    datasets = [_load_dataset(config) for config in DATASET_CONFIGS]
    _render_index_html(INDEX_PATH, datasets)


if __name__ == "__main__":
    main()
