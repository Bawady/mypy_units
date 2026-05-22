"""Speed and distance calculations — dimension- and scale-checked with mypy_units.

Run:         python examples/speed.py
Type-check:  mypy examples/speed.py

Scale-check rule: the declared unit of each parameter and return value fully
determines whether the arithmetic is accepted.  To convert between units via
a scalar factor, wrap the factor in ``ConversionFactor(x)``.  This tells the
plugin that the scalar is a unit-conversion factor (inverse scale semantics:
multiplying the value by k converts to a k-times-smaller unit).  Plain
scalars have no effect on the inferred unit type.
"""

from __future__ import annotations

from typing import Literal

from mypy_units import Array, Quantity, QuantityArray, ScaleFactor
from mypy_units.units import (
    hour,
    kilometer,
    kilometer_per_hour,
    meter,
    meter_per_second,
    second,
)


def speed(distance: meter, t: second) -> meter_per_second:
    """v = d / t   (m / s → m/s)"""
    return distance / t


def speed_kmh(distance: kilometer, t: hour) -> kilometer_per_hour:
    """v = d / t   (km / h → km/h)"""
    return distance / t


def speed_in_kmh(distance: meter, t: second) -> kilometer_per_hour:
    """v = d / t converted to km/h via ConversionFactor(3.6).

    1 m/s = 3.6 km/h, so multiplying the m/s value by 3.6 gives km/h.
    Wrapping in ConversionFactor tells the plugin to apply inverse-scale
    semantics: the type scale is divided by 3.6, yielding km/h.
    """
    return ScaleFactor(3.6) * distance / t


def travel_time(distance: kilometer, v: kilometer_per_hour) -> hour:
    """t = d / v   (km / (km/h) → h)"""
    return distance / v


def travel_time_in_hours(distance: meter, v: meter_per_second) -> hour:
    """t = d / v converted to hours via ConversionFactor(3600).

    m / (m/s) = second; dividing by ConversionFactor(3600) converts to hours
    because 1 hour = 3600 seconds.
    """
    return (distance / v) / ScaleFactor(3600)


def travel_time_wrong(distance: meter, v: Array[Literal["m/s"]]) -> QuantityArray[hour]:
    """t = d / v — WRONG: km / (m/s) has scale 1000 s, not 3600 s (= 1 h).

    mypy flags this because 1000 s ≠ 3600 s; no literal scalar is present to
    bridge the gap.
    """
    return distance / v / ScaleFactor(3600)


if __name__ == "__main__":
    d_m: meter = Quantity(100.0)
    t_s: second = Quantity(3600.0)
    v_ms: meter_per_second = speed(d_m, t_s)
    print(f"Speed: {v_ms.value:.4f} m/s")

    d_km: kilometer = Quantity(100.0)
    t_h: hour = Quantity(2.0)
    v_kmh: kilometer_per_hour = speed_kmh(d_km, t_h)
    print(f"Speed: {v_kmh.value:.1f} km/h")

    t2: hour = travel_time(d_km, v_kmh)
    print(f"Travel time: {t2.value:.1f} h")

    d_m2: meter = Quantity(100.0)
    t_s2: second = Quantity(50.0)
    v_kmh2: kilometer_per_hour = speed_in_kmh(d_m2, t_s2)
    print(f"Speed: {v_kmh2.value:.1f} km/h")

    v_ms2: meter_per_second = speed(d_m2, t_s2)
    t3: hour = travel_time_in_hours(d_m2, v_ms2)
    print(f"Travel time: {t3.value:.6f} h")

    # Conversions
    d_km_from_m: kilometer = d_m / ScaleFactor(1000)
    v_mkh_from_ms: kilometer_per_hour = d_m / t_s * ScaleFactor(3.6)
