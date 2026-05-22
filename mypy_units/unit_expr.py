"""Unit expression type constructors for physical unit checking.

This module provides `Scalar` and `Array` classes that can be subscripted with
string literals containing pint-parseable unit expressions. The subscript is
evaluated at type-checking time by the mypy plugin to produce canonical Quantity
or QuantityArray types.

Example::

    from mypy_units import Scalar, Array

    def speed(d: Scalar["km"], t: Scalar["hour"]) -> Scalar["km/h"]:
        return d / t

    def speeds(d: Array["km"], t: Array["hour"]) -> Array["km/h"]:
        return d / t

The string syntax supports full pint expressions like "km/h", "m/s**2", etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if not TYPE_CHECKING:
    from typing import Literal

    from mypy_units.array_quantity import QuantityArray
    from mypy_units.dimension import to_base_literal
    from mypy_units.quantity import Quantity

    class Scalar:
        def __class_getitem__(cls, item: Any) -> Any:
            canonical = to_base_literal(item)
            return Quantity[Literal[canonical]]

    class Array:
        def __class_getitem__(cls, item: Any) -> Any:
            canonical = to_base_literal(item)
            return QuantityArray[Quantity[Literal[canonical]]]
else:

    class Scalar: ...

    class Array: ...
