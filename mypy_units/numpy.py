"""Dimension-aware wrappers for common numpy functions.

Use these instead of calling ``np.<func>`` directly on ``Quantity`` values so
that the mypy plugin can track the resulting dimensionality::

    from mypy_units.numpy import power, sqrt
    from mypy_units.units import second, acceleration, length

    def accel(l: length, t: second) -> acceleration:
        return l / power(t, 2)          # [length] / [time]**2  ✓

    def rms_length(area: Quantity[Literal["[length] ** 2"]]) -> length:
        return sqrt(area)               # ([length]**2)**(1/2) = [length]  ✓

The wrappers also ensure that runtime numpy operations receive the underlying
numeric value (float or ndarray) rather than the Quantity wrapper.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from mypy_units.quantity import Quantity


def power(base: Quantity[Any], exp: int | float) -> Quantity[Any]:
    """Raise a dimensioned quantity to a power (integer or fractional).

    The mypy plugin tracks the resulting dimension: ``[length] ** 2``,
    ``[time] ** (1/2)``, etc.
    """
    v = base._value if isinstance(base, Quantity) else base
    return Quantity(np.power(v, exp))


def sqrt(x: Quantity[Any]) -> Quantity[Any]:
    """Square root of a dimensioned quantity.

    Equivalent to ``power(x, 0.5)``.  The plugin computes the result
    dimension as ``dim ** (1/2)``.
    """
    v = x._value if isinstance(x, Quantity) else x
    return Quantity(np.sqrt(v))


def cbrt(x: Quantity[Any]) -> Quantity[Any]:
    """Cube root of a dimensioned quantity.

    Equivalent to ``power(x, 1/3)``.  The plugin computes the result
    dimension as ``dim ** (1/3)``.
    """
    v = x._value if isinstance(x, Quantity) else x
    return Quantity(np.cbrt(v))
