"""Demonstrates unit type hints for both scalar floats and numpy arrays.

Scalar functions use plain unit aliases (``meter``, ``second``, …).
Array functions use ``Array[unit]`` to annotate numpy array operands.
Both are fully dimension-checked by the mypy plugin.
"""

from __future__ import annotations

import numpy as np

from mypy_units import Array, Quantity, QuantityArray
from mypy_units.units import (
    kilogram,
    meter,
    meter_per_second,
    meter_per_second_squared,
    newton,
    pascal,
    second,
    square_meter,
)

# ---------------------------------------------------------------------------
# Scalar functions — unit hint is a plain float alias
# ---------------------------------------------------------------------------


def speed(distance: meter, t: second) -> meter_per_second:
    return distance / t


def accel(v: meter_per_second, t: second) -> meter_per_second_squared:
    return v / t


def accel2(dist: meter, t: second) -> meter_per_second_squared:
    """Uses np.power — plugin tracks [length] / [time]**2."""
    return dist / np.power(t, 2)


# ---------------------------------------------------------------------------
# Array functions — unit hint is Array[alias]
# ---------------------------------------------------------------------------


def speed_arr(distance: Array[meter], t: Array[second]) -> Array[meter_per_second]:
    return distance / t


def accel_arr(v: Array[meter_per_second], t: Array[second]) -> Array[meter_per_second_squared]:
    return v / t


def accel2_arr(dist: Array[meter], t: Array[second]) -> Array[meter_per_second_squared]:
    """Uses np.power on an array — plugin still tracks the dimension."""
    return dist / np.power(t, 2)


# ---------------------------------------------------------------------------
# Scalar demo
# ---------------------------------------------------------------------------

d_scalar: meter = Quantity(10.0)
t_scalar: second = Quantity(2.0)
v_scalar: meter_per_second = speed(d_scalar, t_scalar)
print(f"scalar speed:  {v_scalar} m/s")
print(f"scalar accel2: {accel2(d_scalar, t_scalar)} m/s²")

dist: meter = Quantity(10.0)
m_kg: kilogram = Quantity(2.0)
t_1: second = Quantity(1.0)

p: pascal = m_kg / (dist * t_1**2)
f: newton = p * dist**2
print(f"pressure: {p} Pa,  force: {f} N")

# ---------------------------------------------------------------------------
# Array demo
# ---------------------------------------------------------------------------

d_arr: Array[meter] = QuantityArray(np.array([10.0, 20.0, 30.0]))
t_arr: Array[second] = QuantityArray(np.array([2.0, 4.0, 5.0]))
print(f"array speeds:  {speed_arr(d_arr, t_arr)}")
print(f"array accels:  {accel2_arr(d_arr, t_arr)}")

# sqrt: recover Array[meter] from Array[square_meter]
area_arr: Array[square_meter] = QuantityArray(np.array([4.0, 9.0, 16.0]))
side_arr: Array[meter] = np.sqrt(area_arr)
print(f"side lengths:  {side_arr}")

# sqrt on a scalar square_meter quantity
area_scalar: square_meter = Quantity(9.0)
side_scalar: meter = np.sqrt(area_scalar)
print(f"scalar side:   {side_scalar}")
