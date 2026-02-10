from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from orders_of_magnitude import render_index_html

if TYPE_CHECKING:
    from pathlib import Path


def test_render_index_css_copies_template(tmp_path: Path) -> None:
    template_css = tmp_path / "template.css"
    output_css = tmp_path / "index.css"
    expected_css = "body { color: red; }\n"
    template_css.write_text(expected_css, encoding="utf-8")

    render_index_html._render_index_css(output_css, template_css)

    assert output_css.read_text(encoding="utf-8") == expected_css


def test_render_index_css_requires_template(tmp_path: Path) -> None:
    template_css = tmp_path / "missing.css"
    output_css = tmp_path / "index.css"

    with pytest.raises(
        FileNotFoundError, match=rf"Missing CSS template at {template_css}\."
    ):
        render_index_html._render_index_css(output_css, template_css)


def test_main_writes_default_files_in_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    render_index_html.main([])

    output_html = tmp_path / render_index_html.DEFAULT_HTML_FILENAME
    output_css = tmp_path / render_index_html.DEFAULT_CSS_FILENAME
    assert output_html.exists()
    assert output_css.exists()
    assert f'href="{render_index_html.DEFAULT_CSS_FILENAME}"' in output_html.read_text(
        encoding="utf-8"
    )


def test_main_respects_custom_output_paths(tmp_path: Path) -> None:
    output_html = tmp_path / "index.html"
    output_css = tmp_path / "index.css"

    render_index_html.main(
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

    render_index_html.main(
        ["--html", str(output_html), "--css", str(output_css)],
    )

    assert output_html.exists()
    assert output_css.exists()
    assert 'href="../assets/main.css"' in output_html.read_text(encoding="utf-8")
