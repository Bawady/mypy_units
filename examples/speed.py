"""Speed and distance calculations — dimension-checked with mypy_units.

Run:         python examples/speed.py
Type-check:  mypy examples/speed.py
"""
from __future__ import annotations

from mypy_units import Quantity
from mypy_units.units import meter, meter_per_second, second


def speed(distance: meter, t: second) -> meter_per_second:
    """v = d / t"""
    return distance / t


def travel_time(distance: meter, v: meter_per_second) -> second:
    """t = d / v"""
    return distance / v


if __name__ == "__main__":
    d: meter = Quantity(100.0)
    t: second = Quantity(3600.0)
    v = speed(d, t)
    print(f"Speed: {v.value:.4f} m/s")
    t2: second = travel_time(d, Quantity(28.0))
    print(f"Travel time at 28 m/s: {t2.value:.0f} s  ({t2.value / 3600:.2f} h)")
