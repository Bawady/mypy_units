"""Shared helpers for running mypy on inline Python source fixtures."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

PLUGIN_CONFIG = """\
[mypy]
python_version = 3.11
plugins = mypy_units.plugin

[mypy-pintrs]
ignore_missing_imports = True
"""

PREAMBLE = """\
from __future__ import annotations
import numpy as np
from typing import Literal
from mypy_units import Array, Quantity, QuantityArray, ScaleFactor, Scalar
from mypy_units.units import (
    meter, kilometer, second, kilogram, radian,
    hour, kilometer_per_hour,
    meter_per_second, meter_per_second_squared,
    square_meter,
)
from mypy_units.numpy import power, sqrt, cbrt
"""


@pytest.fixture()
def mypy_fixture(tmp_path: Path):
    """Return a callable that runs mypy on a source string and returns stdout."""
    cfg = tmp_path / "mypy.ini"
    cfg.write_text(PLUGIN_CONFIG)

    def run(source: str) -> str:
        import mypy.api

        src = tmp_path / "check.py"
        src.write_text(PREAMBLE + textwrap.dedent(source), encoding="utf-8")
        stdout, stderr, _ = mypy.api.run([str(src), f"--config-file={cfg}", "--no-error-summary"])
        return stdout + stderr

    return run
