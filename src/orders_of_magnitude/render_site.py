"""Render site HTML and CSS from datasets and templates."""

from __future__ import annotations

import argparse
import html
import logging
import math
import os
import textwrap
from pathlib import Path

from logscale import order_of_magnitude

from orders_of_magnitude import datasets

PACKAGE_ROOT = Path(__file__).resolve().parent
HTML_TEMPLATE_ROOT = PACKAGE_ROOT / "templates"
HTML_TEMPLATE_PATH = HTML_TEMPLATE_ROOT / "index.html"
CSS_TEMPLATE_PATH = HTML_TEMPLATE_ROOT / "index.css"
DEFAULT_HTML_FILENAME = "orders-of-magnitude.html"
DEFAULT_CSS_FILENAME = "orders-of-magnitude.css"
TABLES_PLACEHOLDER = "{{ tables }}"
CSS_HREF_PLACEHOLDER = "{{ css_href }}"
HTML_PRINT_WIDTH = 80
TABLE_HEADERS: tuple[str, ...] = (
    "Order of magnitude",
    "Name",
    "Value",
    "Fields",
    "Source",
)
LOGGER = logging.getLogger(__name__)


def _read_text(path: Path, label: str) -> str:
    """Return UTF-8 text from ``path`` or raise if the file is missing."""
    if not path.exists():
        message = f"Missing {label} at {path}."
        raise FileNotFoundError(message)
    return path.read_text(encoding="utf-8")


def _scientific_parts(value: float) -> tuple[str, int]:
    """Return mantissa and exponent parsed from ``logscale.order_of_magnitude``."""
    if not math.isfinite(value):
        message = "Observable value must be a finite number."
        raise ValueError(message)
    scientific_notation = order_of_magnitude(value)
    mantissa, separator, exponent_str = scientific_notation.partition("e")
    if not separator:
        message = (
            f"order_of_magnitude returned an unexpected value: {scientific_notation!r}."
        )
        raise ValueError(message)

    try:
        exponent = int(exponent_str)
    except ValueError as exc:
        message = (
            f"order_of_magnitude returned an invalid exponent: {scientific_notation!r}."
        )
        raise ValueError(message) from exc

    return mantissa, exponent


def _render_observable_row(
    observable: datasets.Observable, indent: str, source_ref: int
) -> str:
    """Render one observable as an HTML table row."""
    mantissa, exponent = _scientific_parts(observable.value)
    unit = html.escape(observable.unit)
    value = f"{mantissa} &times; 10<sup>{exponent}</sup> {unit}"
    return "\n".join(
        (
            f"{indent}<tr>",
            f'{indent}  <td class="math">10<sup>{exponent}</sup> {unit}</td>',
            f"{indent}  <td>{html.escape(observable.name)}</td>",
            f'{indent}  <td class="math">{value}</td>',
            f"{indent}  <td>{html.escape(observable.fields)}</td>",
            f"{indent}  <td>[{source_ref}]</td>",
            f"{indent}</tr>",
        )
    )


def _source_references(loaded_datasets: list[datasets.Dataset]) -> dict[str, int]:
    """Return source text -> reference number, preserving first-seen order."""
    references: dict[str, int] = {}
    for dataset in loaded_datasets:
        for observable in dataset.observables:
            if observable.source not in references:
                references[observable.source] = len(references) + 1
    return references


def _render_dataset_section(
    dataset: datasets.Dataset, indent: str, source_references: dict[str, int]
) -> str:
    """Render one dataset as an HTML ``section`` containing a table."""
    header_indent = f"{indent}        "
    row_indent = f"{indent}      "
    headers = "\n".join(f"{header_indent}<th>{label}</th>" for label in TABLE_HEADERS)
    rows = "\n".join(
        _render_observable_row(
            observable,
            row_indent,
            source_references[observable.source],
        )
        for observable in dataset.observables
    )
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


def _render_sources_section(source_references: dict[str, int], indent: str) -> str:
    """Render deduplicated source references displayed after the dataset tables."""
    item_indent = f"{indent}    "
    items = "\n".join(
        _render_source_item(source, item_indent, reference)
        for source, reference in source_references.items()
    )
    return "\n".join(
        (
            f'{indent}<section class="sources">',
            f"{indent}  <h2>Sources</h2>",
            f"{indent}  <ul>",
            items,
            f"{indent}  </ul>",
            f"{indent}</section>",
        )
    )


def _render_source_item(source: str, indent: str, reference: int) -> str:
    """Render one source reference using Prettier-compatible HTML wrapping."""
    text = f"[{reference}] {html.escape(source)}"
    inline_item = f"{indent}<li>{text}</li>"
    if len(inline_item) <= HTML_PRINT_WIDTH:
        return inline_item

    text_indent = f"{indent}  "
    wrapped_text = textwrap.wrap(
        text,
        width=HTML_PRINT_WIDTH - len(text_indent),
    )
    return "\n".join(
        (
            f"{indent}<li>",
            *(f"{text_indent}{line}" for line in wrapped_text),
            f"{indent}</li>",
        )
    )


def _render_html_page(
    template_text: str,
    loaded_datasets: list[datasets.Dataset],
    stylesheet_href: str,
) -> str:
    """Fill the HTML template with the stylesheet href and rendered datasets."""
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
    references = _source_references(loaded_datasets)
    sections = [
        _render_dataset_section(dataset, indent, references)
        for dataset in loaded_datasets
    ]
    sections.append(_render_sources_section(references, indent))

    template_text = template_text.replace(
        CSS_HREF_PLACEHOLDER, html.escape(stylesheet_href, quote=True)
    )
    return template_text.replace(
        placeholder_line,
        "\n\n".join(sections),
        1,
    )


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


def _write_action(path: Path) -> str:
    """Return ``created`` when ``path`` is new, otherwise ``updated``."""
    if path.exists():
        return "updated"
    return "created"


def render_site(html_output_path: Path, css_output_path: Path) -> None:
    """Render site HTML and CSS files to the provided output paths."""
    html_action = _write_action(html_output_path)
    css_action = _write_action(css_output_path)
    stylesheet_href = _compute_stylesheet_href(html_output_path, css_output_path)
    loaded_datasets = datasets.load_datasets()
    html_template = _read_text(HTML_TEMPLATE_PATH, "HTML template")
    css_template = _read_text(CSS_TEMPLATE_PATH, "CSS template")

    html_output_path.write_text(
        _render_html_page(html_template, loaded_datasets, stylesheet_href),
        encoding="utf-8",
    )
    css_output_path.write_text(css_template, encoding="utf-8")
    LOGGER.info("%s HTML file: %s", html_action.capitalize(), html_output_path)
    LOGGER.info("%s CSS file: %s", css_action.capitalize(), css_output_path)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for rendering the site assets."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    html_output_path, css_output_path = _parse_cli_args(argv)
    render_site(html_output_path, css_output_path)


if __name__ == "__main__":
    main()
