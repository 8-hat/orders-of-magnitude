"""Render site HTML and CSS from dataset YAML files and templates."""

from __future__ import annotations

import argparse
import html
import os
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pint
import yaml
from pint import errors as pint_errors

PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PACKAGE_ROOT / "data"
HTML_TEMPLATE_ROOT = PACKAGE_ROOT / "templates"
HTML_TEMPLATE_PATH = HTML_TEMPLATE_ROOT / "index.html"
CSS_TEMPLATE_PATH = HTML_TEMPLATE_ROOT / "index.css"
DEFAULT_HTML_FILENAME = "orders-of-magnitude.html"
DEFAULT_CSS_FILENAME = "orders-of-magnitude.css"
TABLES_PLACEHOLDER = "{{ tables }}"
CSS_HREF_PLACEHOLDER = "{{ css_href }}"
TABLE_HEADERS: tuple[str, ...] = ("Order of magnitude", "Name", "Value")
OBSERVABLE_FIELDS: tuple[str, ...] = ("name", "value", "unit")
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
    """Return UTF-8 text from ``path`` or raise if the file is missing."""
    if not path.exists():
        message = f"Missing {label} at {path}."
        raise FileNotFoundError(message)
    return path.read_text(encoding="utf-8")


def _ensure_mapping(item: object, message: str) -> dict[str, object]:
    """Validate that ``item`` is a mapping and return it."""
    if isinstance(item, dict):
        return item
    raise TypeError(message)


def _ensure_string(value: object, message: str) -> str:
    """Validate that ``value`` is a string and return it."""
    if isinstance(value, str):
        return value
    raise TypeError(message)


def _parse_decimal(value: object, message: str) -> Decimal:
    """Convert a numeric-like value to ``Decimal`` while rejecting booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(message)
    return Decimal(str(value))


def _parse_observable(item: object, index: int, target_unit: str) -> Observable:
    """Parse one observable mapping, validate required fields, and normalize units."""
    observable = _ensure_mapping(item, f"Observable {index} must be a mapping.")
    for field in OBSERVABLE_FIELDS:
        if field not in observable:
            message = f"Observable {index} missing '{field}'."
            raise ValueError(message)

    name = _ensure_string(
        observable["name"], f"Observable {index} field 'name' must be a string."
    )
    unit = _ensure_string(
        observable["unit"], f"Observable {index} field 'unit' must be a string."
    )
    value = _parse_decimal(
        observable["value"], f"Observable {index} field 'value' must be a number."
    )

    value = _convert_to_target_unit(value, unit, target_unit, index)
    return Observable(name=name, value=value, unit=target_unit)


def _convert_to_target_unit(
    value: Decimal, unit: str, target_unit: str, index: int
) -> Decimal:
    """Convert ``value`` from ``unit`` to ``target_unit`` and return a ``Decimal``."""
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
    """Return mantissa and exponent rounded for scientific notation display."""
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
    """Load and validate a dataset YAML file, converting all values to one unit."""
    raw = _ensure_mapping(
        yaml.safe_load(_read_text(path, "YAML file")),
        "Top-level YAML must be a mapping with an 'observables' key.",
    )
    title = _ensure_string(raw.get("title"), "YAML 'title' must be a string.")
    items = raw.get("observables")
    if not isinstance(items, list):
        message = "YAML 'observables' must be a list."
        raise TypeError(message)

    observables = [
        _parse_observable(item, index, target_unit) for index, item in enumerate(items)
    ]
    return Dataset(title=title, observables=observables)


def _render_observable_row(observable: Observable, indent: str) -> str:
    """Render one observable as an HTML table row."""
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


def _render_dataset_section(dataset: Dataset, indent: str) -> str:
    """Render one dataset as an HTML ``section`` containing a table."""
    row_indent = f"{indent}      "
    rows = "\n".join(
        _render_observable_row(observable, row_indent)
        for observable in dataset.observables
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


def _write_html_page(
    html_output_path: Path,
    html_template_path: Path,
    datasets: list[Dataset],
    stylesheet_href: str,
) -> None:
    """Fill the HTML template with dataset tables and write the output page."""
    template_text = _read_text(html_template_path, "HTML template")
    if CSS_HREF_PLACEHOLDER not in template_text:
        message = f"Template missing CSS href placeholder '{CSS_HREF_PLACEHOLDER}'."
        raise ValueError(message)
    placeholder_line = next(
        (line for line in template_text.splitlines() if TABLES_PLACEHOLDER in line),
        None,
    )
    if placeholder_line is None:
        message = f"Template missing tables placeholder '{TABLES_PLACEHOLDER}'."
        raise ValueError(message)

    indent = placeholder_line.split(TABLES_PLACEHOLDER, 1)[0]
    tables_html = "\n\n".join(
        _render_dataset_section(dataset, indent) for dataset in datasets
    )
    rendered_template = template_text.replace(
        CSS_HREF_PLACEHOLDER, html.escape(stylesheet_href, quote=True)
    )
    html_output_path.write_text(
        rendered_template.replace(placeholder_line, tables_html, 1), encoding="utf-8"
    )


def _write_css_file(css_output_path: Path, css_template_path: Path) -> None:
    """Copy the CSS template content into the CSS output path."""
    css_output_path.write_text(
        _read_text(css_template_path, "CSS template"), encoding="utf-8"
    )


def _load_datasets() -> list[Dataset]:
    """Load every configured dataset source."""
    return [_load_dataset(path, target) for path, target in DATASET_SOURCES]


def _compute_stylesheet_href(html_path: Path, css_path: Path) -> str:
    """Build a browser-safe CSS href relative to the HTML file when possible."""
    resolved_html_path = html_path.resolve()
    resolved_css_path = css_path.resolve()
    try:
        relative_css_path = os.path.relpath(
            resolved_css_path, start=resolved_html_path.parent
        )
    except ValueError:
        # This can happen on Windows when paths are on different drives.
        return resolved_css_path.as_posix()
    return Path(relative_css_path).as_posix()


def _parse_cli_args(argv: list[str] | None) -> tuple[Path, Path]:
    """Parse CLI options and return HTML and CSS output paths."""
    parser = argparse.ArgumentParser(
        description=(
            "Render orders-of-magnitude HTML and CSS files from package datasets."
        )
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=Path(DEFAULT_HTML_FILENAME),
        help=f"Output HTML file path (default: {DEFAULT_HTML_FILENAME}).",
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=Path(DEFAULT_CSS_FILENAME),
        help=f"Output CSS file path (default: {DEFAULT_CSS_FILENAME}).",
    )
    parsed = parser.parse_args(argv)
    return parsed.html, parsed.css


def render_site(html_output_path: Path, css_output_path: Path) -> None:
    """Render site HTML and CSS files to the provided output paths."""
    stylesheet_href = _compute_stylesheet_href(html_output_path, css_output_path)
    datasets = _load_datasets()
    _write_html_page(
        html_output_path,
        HTML_TEMPLATE_PATH,
        datasets,
        stylesheet_href=stylesheet_href,
    )
    _write_css_file(css_output_path, CSS_TEMPLATE_PATH)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for rendering the site assets."""
    html_output_path, css_output_path = _parse_cli_args(argv)
    render_site(html_output_path, css_output_path)


if __name__ == "__main__":
    main()
