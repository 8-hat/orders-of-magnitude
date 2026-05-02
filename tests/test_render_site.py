from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from orders_of_magnitude import datasets, render_site

if TYPE_CHECKING:
    from pathlib import Path


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
        datasets,
        "load_datasets",
        lambda: [
            datasets.Dataset(
                title="Demo",
                observables=[
                    datasets.Observable(
                        name="First",
                        fields="field",
                        source="Shared source",
                        value=1.0,
                        unit="m",
                    ),
                    datasets.Observable(
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


def test_source_references_deduplicate_by_text() -> None:
    loaded_datasets = [
        datasets.Dataset(
            title="A",
            observables=[
                datasets.Observable(
                    name="one",
                    fields="f",
                    source="Shared source",
                    value=1.0,
                    unit="m",
                ),
                datasets.Observable(
                    name="two",
                    fields="f",
                    source="Shared source",
                    value=2.0,
                    unit="m",
                ),
            ],
        ),
        datasets.Dataset(
            title="B",
            observables=[
                datasets.Observable(
                    name="three",
                    fields="f",
                    source="Other source",
                    value=3.0,
                    unit="m",
                ),
            ],
        ),
    ]

    assert render_site._source_references(loaded_datasets) == {
        "Shared source": 1,
        "Other source": 2,
    }


def test_render_source_item_keeps_short_references_inline() -> None:
    assert (
        render_site._render_source_item("Short source", "        ", 1)
        == "        <li>[1] Short source</li>"
    )


def test_render_source_item_wraps_long_references_like_prettier() -> None:
    source = "S. Navas et al. (Particle Data Group), Phys. Rev. D 110, 030001 (2024)"
    expected = (
        "        <li>\n"
        "          [1] S. Navas et al. (Particle Data Group), Phys. Rev. "
        "D 110, 030001\n"
        "          (2024)\n"
        "        </li>"
    )

    assert render_site._render_source_item(source, "        ", 1) == expected


def test_generated_site_matches_committed_site(
    tmp_path: Path,
) -> None:
    output_html = tmp_path / "index.html"
    output_css = tmp_path / "index.css"

    render_site.render_site(output_html, output_css)

    committed_html = render_site.PACKAGE_ROOT.parent.parent / "index.html"
    committed_css = render_site.PACKAGE_ROOT.parent.parent / "index.css"
    assert output_html.read_text(encoding="utf-8") == committed_html.read_text(
        encoding="utf-8"
    )
    assert output_css.read_text(encoding="utf-8") == committed_css.read_text(
        encoding="utf-8"
    )
