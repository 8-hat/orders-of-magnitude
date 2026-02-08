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
