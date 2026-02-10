# orders-of-magnitude

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

[![Coverage][coverage-badge]][coverage-link]

## CLI

Run `uvx orders-of-magnitude` to generate `orders-of-magnitude.html` and
`orders-of-magnitude.css` in the current working directory.

## Update index files

1. Edit `src/orders_of_magnitude/data/lengths.yml` (and any other dataset
   files).
2. Edit `src/orders_of_magnitude/templates/index.html` for layout and
   `src/orders_of_magnitude/templates/index.css` for styles.
3. Run `nox -s render_index_html`.
4. Commit the updated `index.html` and `index.css`.

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/8-hat/orders-of-magnitude/workflows/CI/badge.svg
[actions-link]:             https://github.com/8-hat/orders-of-magnitude/actions
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/orders-of-magnitude
[conda-link]:               https://github.com/conda-forge/orders-of-magnitude-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/8-hat/orders-of-magnitude/discussions
[pypi-link]:                https://pypi.org/project/orders-of-magnitude/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/orders-of-magnitude
[pypi-version]:             https://img.shields.io/pypi/v/orders-of-magnitude
[rtd-badge]:                https://readthedocs.org/projects/orders-of-magnitude/badge/?version=latest
[rtd-link]:                 https://orders-of-magnitude.readthedocs.io/en/latest/?badge=latest
[coverage-badge]:           https://codecov.io/github/8-hat/orders-of-magnitude/branch/main/graph/badge.svg
[coverage-link]:            https://codecov.io/github/8-hat/orders-of-magnitude

<!-- prettier-ignore-end -->
