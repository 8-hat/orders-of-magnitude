from __future__ import annotations

import importlib.metadata

import orders_of_magnitude as m


def test_version():
    assert importlib.metadata.version("orders_of_magnitude") == m.__version__
