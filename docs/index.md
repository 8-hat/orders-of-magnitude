# orders-of-magnitude

Here you can document whatever you'd like on your main page. Common choices
include installation instructions, a minimal usage example, BibTex citations,
and contribution guidelines.

See [this link](https://squidfunk.github.io/mkdocs-material/reference/) for all
the easy references and components you can use with mkdocs-material, or feel
free to go through through
[from the top](https://squidfunk.github.io/mkdocs-material/).

## Installation

You can install this package via running:

```bash
pip install orders_of_magnitude
```

## Update index files

1. Edit `src/orders_of_magnitude/data/lengths.yml` (and any other dataset
   files).
2. Edit `src/orders_of_magnitude/templates/index.html` for layout and
   `src/orders_of_magnitude/templates/index.css` for styles.
3. Run `nox -s render_index_html`.
4. Commit the updated `index.html` and `index.css`.
