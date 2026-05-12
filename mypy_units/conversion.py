"""ConversionFactor — explicit unit-conversion wrapper for mypy_units.

Usage::

    from mypy_units import ConversionFactor
    from mypy_units.units import meter, second, kilometer_per_hour, hour

    def speed_in_kmh(d: meter, t: second) -> kilometer_per_hour:
        return ConversionFactor(3.6) * d / t

    def travel_time_hours(d: meter, v: meter_per_second) -> hour:
        return (d / v) / ConversionFactor(3600)

Semantics
---------
At **runtime** ``ConversionFactor(x)`` is transparent: it multiplies or
divides the wrapped value by ``x``, producing the same numeric result as
using the bare scalar.

At **static analysis** time the mypy plugin treats a ``ConversionFactor(x)``
operand as a *unit-conversion factor*, applying the invariant
``physical = value × scale`` in both directions:

* ``quantity[scale S] * ConversionFactor(k)``  →  scale becomes ``S / k``
* ``quantity[scale S] / ConversionFactor(k)``  →  scale becomes ``S * k``

Plain scalars (bare float/int literals or variables) do **not** affect the
inferred unit type; only ``ConversionFactor``-wrapped values do.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any


class ConversionFactor:
    """Signals unit-conversion intent to the mypy_units plugin.

    Wrap the conversion factor in ``ConversionFactor(x)`` to let the plugin
    track the resulting unit type through the arithmetic expression.
    """

    __slots__ = ("value",)

    def __init__(self, value: float | int) -> None:
        self.value = float(value)

    def __repr__(self) -> str:
        return f"ConversionFactor({self.value!r})"

    # ------------------------------------------------------------------
    # Runtime arithmetic — behave like the bare scalar value.
    # The TYPE CHECKER never sees these methods (TYPE_CHECKING is False
    # at runtime), so mypy falls back to Quantity.__rmul__ / __truediv__
    # which the plugin already hooks.
    # ------------------------------------------------------------------

    if not TYPE_CHECKING:
        def __mul__(self, other: Any) -> Any:
            # Defer to Quantity.__rmul__ for Quantity / QuantityArray args.
            if hasattr(other, "_value") and not isinstance(other, (int, float, complex)):
                return NotImplemented
            return self.value * other

        def __rmul__(self, other: Any) -> Any:
            # Called as other * self.value (e.g. inside Quantity.__rmul__).
            return other * self.value

        def __rtruediv__(self, other: Any) -> Any:
            # Called as other / self.value (e.g. inside Quantity.__truediv__).
            return other / self.value
