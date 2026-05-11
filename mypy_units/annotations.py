from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    unit_str: str  # e.g. "meter", "km/h", "kg*m/s^2"
