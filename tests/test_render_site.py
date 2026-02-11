from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from orders_of_magnitude import render_site

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

    render_site.main([])

    output_html = tmp_path / render_site.DEFAULT_HTML_FILENAME
    output_css = tmp_path / render_site.DEFAULT_CSS_FILENAME
    assert output_html.exists()
    assert output_css.exists()
    html_text = output_html.read_text(encoding="utf-8")
    assert f'href="{render_site.DEFAULT_CSS_FILENAME}"' in html_text


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
