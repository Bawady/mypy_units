"""Convenient type aliases for unit annotations.

This module provides two ways to create unit type annotations:

1. **Pre-defined base units** for creating compound units::

    from mypy_units.typing import m, s

    # Create compound units (these are actual types)
    speed = m / s  # type: ignore[valid-type]
    acceleration = m / s ** 2

    def travel(s: speed, t: s) -> m:  # type: ignore[valid-type]
        return s * t

2. **String annotations** with Pint syntax (recommended)::

    from mypy_units.quantity import Quantity
    from typing import Literal

    def travel(
        s: Quantity[Literal["m/s"]],
        t: Quantity[Literal["s"]]
    ) -> Quantity[Literal["m"]]:
        return s * t

The string annotation approach is recommended because:
- It works seamlessly with mypy
- Error messages are clear
- No need for type: ignore comments
- Supports full Pint syntax (e.g., "km/h", "m*s**-2")
"""

from __future__ import annotations

from typing import Any, Literal

from mypy_units.dimension import to_base_literal
from mypy_units.quantity import Quantity


class _UnitType:
    """Base unit for creating compound units.

    While you can use arithmetic on these to create compound units,
    mypy doesn't support using the results directly as types.
    Use string annotations instead for best results.
    """

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)

    def __mul__(self, other: _UnitType) -> type[Any]:
        u1 = object.__getattribute__(self, "_name")
        u2 = object.__getattribute__(other, "_name") if isinstance(other, _UnitType) else str(other)
        canonical = to_base_literal(f"{u1} * {u2}")
        return Quantity[Literal[canonical]]  # type: ignore[valid-type, return-value]

    def __truediv__(self, other: _UnitType) -> type[Any]:
        u1 = object.__getattribute__(self, "_name")
        u2 = object.__getattribute__(other, "_name") if isinstance(other, _UnitType) else str(other)
        canonical = to_base_literal(f"{u1} / {u2}")
        return Quantity[Literal[canonical]]  # type: ignore[valid-type, return-value]

    def __pow__(self, exp: int) -> type[Any]:
        u1 = object.__getattribute__(self, "_name")
        if exp == 0:
            return Quantity[Literal["dimensionless"]]  # type: ignore[valid-type, return-value]
        if exp == 1:
            return Quantity[Literal[u1]]  # type: ignore[valid-type, return-value]
        canonical = to_base_literal(f"{u1} ** {exp}")
        return Quantity[Literal[canonical]]  # type: ignore[valid-type, return-value]

    def __repr__(self) -> str:
        return f"Unit({object.__getattribute__(self, '_name')!r})"


# Base SI units
meter = _UnitType("meter")
second = _UnitType("second")
kilogram = _UnitType("kilogram")
ampere = _UnitType("ampere")
kelvin = _UnitType("kelvin")
mole = _UnitType("mole")
candela = _UnitType("candela")

# Common derived units
radian = _UnitType("radian")
hertz = _UnitType("hertz")

# Convenient aliases
m = meter
s = second
kg = kilogram
A = ampere
K = kelvin
mol = mole
cd = candela
rad = radian
Hz = hertz


def unit(unit_str: str) -> type[Any]:  # noqa: N802
    """Create a Quantity type from a Pint unit string.

    This is a runtime helper. For type annotations, prefer using
    Quantity[Literal["..."]] directly or string annotations.

    Example::

        # At runtime
        speed_type = Unit("km/h")

        # In type annotations (recommended)
        def func(x: Quantity[Literal["km/h"]]) -> None: ...
    """
    canonical = to_base_literal(unit_str)
    return Quantity[Literal[canonical]]  # type: ignore[valid-type, return-value]
