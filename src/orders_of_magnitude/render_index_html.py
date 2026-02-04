"""Render index.html from data/observables.yml."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "observables.yml"
INDEX_PATH = ROOT / "index.html"


@dataclass(frozen=True)
class Observable:
    """Structured observable used to render the index table."""

    name: str
    coefficient: Decimal
    power_of_ten: int
    unit: str


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


def _parse_int(value: object, field: str, index: int) -> int:
    if isinstance(value, bool):
        msg = f"Observable {index} field '{field}' must be an integer."
        raise TypeError(msg)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return int(value)
    msg = f"Observable {index} field '{field}' must be an integer."
    raise TypeError(msg)


def _parse_str(value: object, field: str, index: int) -> str:
    if isinstance(value, str):
        return value
    msg = f"Observable {index} field '{field}' must be a string."
    raise TypeError(msg)


def _scientific_parts(coefficient: Decimal, power_of_ten: int) -> tuple[str, int]:
    if coefficient.is_zero():
        return "0", 0
    if not coefficient.is_finite():
        msg = "Observable coefficient must be a finite number."
        raise ValueError(msg)

    sign, digits, exponent = coefficient.as_tuple()
    if not isinstance(exponent, int):
        msg = "Observable coefficient must be a finite number."
        raise TypeError(msg)
    digits_str = "".join(str(digit) for digit in digits)
    exponent_total = power_of_ten + (len(digits) - 1) + exponent

    mantissa = digits_str if len(digits) == 1 else f"{digits_str[0]}.{digits_str[1:]}"

    mantissa = mantissa.rstrip("0").rstrip(".")
    if sign == 1 and mantissa != "0":
        mantissa = f"-{mantissa}"

    return mantissa, exponent_total


def _load_observables(path: Path) -> list[Observable]:
    if not path.exists():
        msg = f"Missing YAML file at {path}."
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "Top-level YAML must be a mapping with an 'observables' key."
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
        coefficient = _parse_decimal(
            _require_field(item, "coefficient", index),
            "coefficient",
            index,
        )
        power_of_ten = _parse_int(
            _require_field(item, "power_of_ten", index),
            "power_of_ten",
            index,
        )
        unit = _parse_str(_require_field(item, "unit", index), "unit", index)

        observables.append(
            Observable(
                name=name,
                coefficient=coefficient,
                power_of_ten=power_of_ten,
                unit=unit,
            )
        )

    return observables


def _render_rows(observables: list[Observable], indent: str) -> str:
    indent_tr = f"{indent}  "
    indent_td = f"{indent_tr}  "

    rows: list[str] = []
    for observable in observables:
        mantissa, exponent = _scientific_parts(
            observable.coefficient, observable.power_of_ten
        )
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


def _render_index_html(index_path: Path, observables: list[Observable]) -> None:
    html_text = index_path.read_text(encoding="utf-8")
    match = re.search(r"(^\s*)<tbody>\s*$", html_text, flags=re.MULTILINE)
    if match is None:
        msg = "Could not find <tbody> tag in index.html."
        raise ValueError(msg)

    indent = match.group(1)
    rows_html = _render_rows(observables, indent)

    block_match = re.search(
        r"(^\s*<tbody>\s*$)(.*?)(^\s*</tbody>\s*$)",
        html_text,
        flags=re.DOTALL | re.MULTILINE,
    )
    if block_match is None:
        msg = "Could not find <tbody> block in index.html."
        raise ValueError(msg)

    new_block = f"{block_match.group(1)}\n{rows_html}\n{block_match.group(3)}"
    updated = (
        html_text[: block_match.start()] + new_block + html_text[block_match.end() :]
    )
    index_path.write_text(updated, encoding="utf-8")


def main() -> None:
    observables = _load_observables(DATA_PATH)
    _render_index_html(INDEX_PATH, observables)


if __name__ == "__main__":
    main()
