"""Dimension-aware wrappers for common numpy functions.

Use these instead of calling ``np.<func>`` directly on ``Quantity`` or
``QuantityArray`` values so that the mypy plugin can track the resulting
dimensionality::

    from mypy_units.numpy import power, sqrt
    from mypy_units.units import meter, second, meter_per_second_squared

    def accel(d: meter, t: second) -> meter_per_second_squared:
        return d / power(t, 2)          # [length] / [time]**2  ✓

    def side(a: Array[square_meter]) -> Array[meter]:
        return sqrt(a)                  # ([length]**2)**(1/2) = [length]  ✓

At runtime ``Quantity`` and ``QuantityArray`` values are already plain
primitives (``float`` / ``ndarray``), so these wrappers simply forward to
the corresponding numpy ufunc.  The dimension of the result is tracked
purely at static-analysis time by the mypy plugin.
"""

from __future__ import annotations

from typing import Any, overload

import numpy as np

from mypy_units.array_quantity import QuantityArray
from mypy_units.quantity import Quantity


@overload
def power(base: Quantity[Any], exp: int | float) -> Quantity[Any]: ...
@overload
def power(base: QuantityArray[Any], exp: int | float) -> QuantityArray[Any]: ...
def power(
    base: Quantity[Any] | QuantityArray[Any], exp: int | float
) -> Quantity[Any] | QuantityArray[Any]:
    """Raise a dimensioned quantity to a power (integer or fractional).

    The mypy plugin tracks the resulting dimension: ``[length] ** 2``,
    ``[time] ** (1/2)``, etc.
    """
    v: Any = base  # runtime value is already a plain float/ndarray
    return np.power(v, exp)  # type: ignore[no-any-return]


@overload
def sqrt(x: Quantity[Any]) -> Quantity[Any]: ...
@overload
def sqrt(x: QuantityArray[Any]) -> QuantityArray[Any]: ...
def sqrt(
    x: Quantity[Any] | QuantityArray[Any],
) -> Quantity[Any] | QuantityArray[Any]:
    """Square root of a dimensioned quantity.

    Equivalent to ``power(x, 0.5)``.  The plugin computes the result
    dimension as ``dim ** (1/2)``.
    """
    v: Any = x  # runtime value is already a plain float/ndarray
    return np.sqrt(v)  # type: ignore[no-any-return]


@overload
def cbrt(x: Quantity[Any]) -> Quantity[Any]: ...
@overload
def cbrt(x: QuantityArray[Any]) -> QuantityArray[Any]: ...
def cbrt(
    x: Quantity[Any] | QuantityArray[Any],
) -> Quantity[Any] | QuantityArray[Any]:
    """Cube root of a dimensioned quantity.

    Equivalent to ``power(x, 1/3)``.  The plugin computes the result
    dimension as ``dim ** (1/3)``.
    """
    v: Any = x  # runtime value is already a plain float/ndarray
    return np.cbrt(v)  # type: ignore[no-any-return]
