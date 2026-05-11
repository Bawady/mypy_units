"""Demonstrates numpy array support — same unit aliases, same dimension checking."""
from __future__ import annotations

import numpy as np

from mypy_units import Quantity
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


def speed(distance: meter, t: second) -> meter_per_second:
    return distance / t


def accel(v: meter_per_second, t: second) -> meter_per_second_squared:
    return v / t


def accel2(dist: meter, t: second) -> meter_per_second_squared:
    return dist / np.power(t, 2)


# scalar
d_scalar: meter = Quantity(10.0)
t_scalar: second = Quantity(2.0)
print(speed(d_scalar, t_scalar).value)  # 5.0

# numpy arrays
d_arr: meter = Quantity(np.array([10.0, 20.0, 30.0]))
t_arr: second = Quantity(np.array([2.0, 4.0, 5.0]))
print(speed(d_arr, t_arr).value)
print(accel2(d_arr, t_arr).value)

# sqrt: recover meter from square_meter
area_arr: square_meter = Quantity(np.array([4.0, 9.0, 16.0]))
side: meter = np.sqrt(area_arr)
print(side.value)

dist: meter = Quantity(10)
m: kilogram = Quantity(2)
t: second = Quantity(1)

p: pascal = m / (dist * t**2)
p2: pascal = m / dist * t**2

f: newton = p * dist**2
f2: newton = p * dist
