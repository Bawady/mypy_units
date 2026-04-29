"""Demonstrates numpy array support — same unit aliases, same dimension checking."""
from typing import Literal

import numpy as np

from mypy_units import Quantity
from mypy_units.units import (
    acceleration,
    force,
    kilometer,
    length,
    mass,
    meter_per_second,
    pressure,
    second,
    time,
    velocity,
)


def speed(distance: kilometer, t: second) -> meter_per_second:
    return distance / t


def accel(v: velocity, t: time) -> acceleration:
    return v / t


def accel2(dist: length, t: time) -> acceleration:
    return dist / np.power(t, 2)


# scalar
d_scalar: kilometer = Quantity(10.0)
t_scalar: second = Quantity(2.0)
print(speed(d_scalar, t_scalar).value)  # 5.0

# numpy arrays
d_arr: kilometer = Quantity(np.array([10.0, 20.0, 30.0]))
t_arr: second = Quantity(np.array([2.0, 4.0, 5.0]))
print(speed(d_arr, t_arr).value)
print(accel2(d_arr, t_arr).value)

# sqrt: recover length from area
area: Quantity[Literal["[length] ** 2"]] = Quantity(np.array([4.0, 9.0, 16.0]))
side: length = np.sqrt(area)
print(side.value)

dist: length = Quantity(10)
m: mass = Quantity(2)
t: time = Quantity(1)

p: pressure = m / (dist * t**2)
p2: pressure = m / dist * t**2

f: force = p * dist**2
f2: force = p * dist

