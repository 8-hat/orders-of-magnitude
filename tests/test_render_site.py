from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import pytest

from orders_of_magnitude import render_site

if TYPE_CHECKING:
    from pathlib import Path


class HtmlTokens(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[tuple[object, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tokens.append(("start", tag, tuple(attrs)))

    def handle_endtag(self, tag: str) -> None:
        self.tokens.append(("end", tag))

    def handle_data(self, data: str) -> None:
        normalized_data = re.sub(r"\s+", " ", data).strip()
        if normalized_data:
            self.tokens.append(("data", normalized_data))


def _html_tokens(text: str) -> list[tuple[object, ...]]:
    parser = HtmlTokens()
    parser.feed(text)
    return parser.tokens


def test_write_css_file_copies_template(tmp_path: Path) -> None:
    template_css = tmp_path / "template.css"
    output_css = tmp_path / "index.css"
    expected_css = "body { color: red; }\n"
    template_css.write_text(expected_css, encoding="utf-8")

    render_site._write_css_file(output_css, template_css)

    assert output_css.read_text(encoding="utf-8") == expected_css


def test_write_css_file_requires_template(tmp_path: Path) -> None:
    template_css = tmp_path / "missing.css"
    output_css = tmp_path / "index.css"

    with pytest.raises(
        FileNotFoundError, match=rf"Missing CSS template at {template_css}\."
    ):
        render_site._write_css_file(output_css, template_css)


def test_main_writes_default_files_in_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        render_site,
        "_load_datasets",
        lambda: [
            render_site.Dataset(
                title="Demo",
                observables=[
                    render_site.Observable(
                        name="First",
                        fields="field",
                        source="Shared source",
                        value=1.0,
                        unit="m",
                    ),
                    render_site.Observable(
                        name="Second",
                        fields="field",
                        source="Shared source",
                        value=10.0,
                        unit="m",
                    ),
                ],
            )
        ],
    )

    render_site.main([])

    output_html = tmp_path / render_site.DEFAULT_HTML_FILENAME
    output_css = tmp_path / render_site.DEFAULT_CSS_FILENAME
    assert output_html.exists()
    assert output_css.exists()
    html_text = output_html.read_text(encoding="utf-8")
    assert f'href="{render_site.DEFAULT_CSS_FILENAME}"' in html_text
    assert "<th>Source</th>" in html_text
    assert html_text.index("<th>Fields</th>") < html_text.index("<th>Source</th>")
    assert "<h2>Sources</h2>" in html_text


def test_main_respects_custom_output_paths(tmp_path: Path) -> None:
    output_html = tmp_path / "index.html"
    output_css = tmp_path / "index.css"

    render_site.main(
        ["--html", str(output_html), "--css", str(output_css)],
    )

    assert output_html.exists()
    assert output_css.exists()
    assert 'href="index.css"' in output_html.read_text(encoding="utf-8")


def test_main_derives_css_href_from_custom_css_path(tmp_path: Path) -> None:
    html_dir = tmp_path / "site"
    css_dir = tmp_path / "assets"
    html_dir.mkdir()
    css_dir.mkdir()
    output_html = html_dir / "index.html"
    output_css = css_dir / "main.css"

    render_site.main(
        ["--html", str(output_html), "--css", str(output_css)],
    )

    assert output_html.exists()
    assert output_css.exists()
    assert 'href="../assets/main.css"' in output_html.read_text(encoding="utf-8")


def test_scientific_parts_uses_logscale_format() -> None:
    assert render_site._scientific_parts(3.48e6) == ("0.35", 7)
    assert render_site._scientific_parts(498) == ("0.50", 3)


def test_load_dataset_requires_fields_key(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    dataset_path.write_text(
        "title: Demo\nobservables:\n  - name: Example\n    value: 1\n    unit: m\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Observable 0 missing 'fields'\."):
        render_site._load_dataset(dataset_path, "m")


def test_load_dataset_requires_source_key(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.yml"
    dataset_path.write_text(
        "title: Demo\n"
        "observables:\n"
        "  - name: Example\n"
        "    value: 1\n"
        "    unit: m\n"
        "    fields: test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Observable 0 missing 'source'\."):
        render_site._load_dataset(dataset_path, "m")


def test_source_references_deduplicate_by_text() -> None:
    datasets = [
        render_site.Dataset(
            title="A",
            observables=[
                render_site.Observable(
                    name="one",
                    fields="f",
                    source="Shared source",
                    value=1.0,
                    unit="m",
                ),
                render_site.Observable(
                    name="two",
                    fields="f",
                    source="Shared source",
                    value=2.0,
                    unit="m",
                ),
            ],
        ),
        render_site.Dataset(
            title="B",
            observables=[
                render_site.Observable(
                    name="three",
                    fields="f",
                    source="Other source",
                    value=3.0,
                    unit="m",
                ),
            ],
        ),
    ]

    assert render_site._source_references(datasets) == {
        "Shared source": 1,
        "Other source": 2,
    }


def test_generated_site_matches_committed_site_ignoring_html_whitespace(
    tmp_path: Path,
) -> None:
    output_html = tmp_path / "index.html"
    output_css = tmp_path / "index.css"

    render_site.render_site(output_html, output_css)

    committed_html = render_site.PACKAGE_ROOT.parent.parent / "index.html"
    committed_css = render_site.PACKAGE_ROOT.parent.parent / "index.css"
    assert _html_tokens(output_html.read_text(encoding="utf-8")) == _html_tokens(
        committed_html.read_text(encoding="utf-8")
    )
    assert output_css.read_text(encoding="utf-8") == committed_css.read_text(
        encoding="utf-8"
    )
