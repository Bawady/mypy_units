from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    import numpy as np

_U_co = TypeVar("_U_co", bound=str, covariant=True)


class Quantity(Generic[_U_co]):
    """A numeric value (scalar or numpy array) carrying a static unit annotation.

    The type parameter is a pint base-unit canonical string (e.g. ``"meter"``).

    **Construction — type-only (standard use)**::

        d: kilometer = Quantity(10)
        d_arr: kilometer = Quantity(np.array([1.0, 2.0, 3.0]))

    **Construction — unit-string (escape hatch)**::

        d = Quantity(10, "km")          # → type kilometer, pint-backed

    **Conversion escape hatch**::

        result = (Quantity(x, "m") / Quantity(t, "s")).to("km/h")
        # → type kilometer_per_hour; pint validates the conversion at runtime

    **Arithmetic** — all standard operations are supported and propagate to the
    wrapped value (float or numpy array).  The *static* type of arithmetic
    results is tracked by the mypy plugin via method hooks.  When either
    operand is pint-backed the result stays pint-backed so that ``.to()`` can
    be called further down the expression chain.
    """

    _value: Any  # raw magnitude in the Quantity's own unit
    _pint_q: Any  # pint.Quantity | None; set when constructed with a unit string

    def __init__(
        self, value: int | float | complex | Quantity[Any] = 0, unit: str | None = None
    ) -> None:
        raw = value._value if isinstance(value, Quantity) else value
        if unit is not None:
            from mypy_units.dimension import _registry

            pq = _registry().Quantity(raw, unit)
            self._pint_q = pq
            self._value = pq.magnitude
        else:
            self._pint_q = None
            self._value = raw

    @classmethod
    def _from_pint(cls, pq: Any) -> Quantity[Any]:
        """Wrap an existing pint Quantity, keeping pint backing."""
        obj = cls.__new__(cls)
        obj._pint_q = pq
        obj._value = pq.magnitude
        return obj

    def to(self, unit: str) -> Quantity[Any]:
        """Convert to *unit* via pint and return a new pint-backed Quantity.

        The static return type is anchored to *unit* by the mypy plugin, acting
        as a checked cast: pint validates the physical compatibility at runtime
        and raises ``pint.DimensionalityError`` for incompatible dimensions.

        Requires a pint-backed Quantity (created with ``Quantity(value, 'unit')``
        or produced by arithmetic on pint-backed Quantities).
        """
        if self._pint_q is None:
            raise TypeError(
                "Quantity.to() is only available on unit-string Quantities. "
                "Create one with Quantity(value, 'unit') to enable pint-backed conversion."
            )
        return Quantity(self._pint_q.to(unit).magnitude)

    @property
    def value(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        if self._pint_q is not None:
            return f"Quantity({self._value!r}, {str(self._pint_q.units)!r})"
        return f"Quantity({self._value!r})"

    def __float__(self) -> float:
        return float(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: object) -> Any:
        v = other._value if isinstance(other, Quantity) else other
        return self._value == v

    def __lt__(self, other: Any) -> Any:
        v = other._value if isinstance(other, Quantity) else other
        return self._value < v

    def __le__(self, other: Any) -> Any:
        v = other._value if isinstance(other, Quantity) else other
        return self._value <= v

    def __gt__(self, other: Any) -> Any:
        v = other._value if isinstance(other, Quantity) else other
        return self._value > v

    def __ge__(self, other: Any) -> Any:
        v = other._value if isinstance(other, Quantity) else other
        return self._value >= v

    # ------------------------------------------------------------------
    # Arithmetic — delegate to the wrapped value; the plugin hooks track
    # the dimension of the result at static analysis time.
    # When either operand is pint-backed the result stays pint-backed.
    # ------------------------------------------------------------------

    def _v(self, other: Any) -> Any:
        return other._value if isinstance(other, Quantity) else other

    def _pq_of(self, other: Any) -> Any:
        return getattr(other, "_pint_q", None)

    def __add__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint(self._pint_q + (opq if opq is not None else self._v(other)))
        return Quantity(self._value + self._v(other))

    def __radd__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint((opq if opq is not None else self._v(other)) + self._pint_q)
        return Quantity(self._v(other) + self._value)

    def __sub__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint(self._pint_q - (opq if opq is not None else self._v(other)))
        return Quantity(self._value - self._v(other))

    def __rsub__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint((opq if opq is not None else self._v(other)) - self._pint_q)
        return Quantity(self._v(other) - self._value)

    def __mul__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint(self._pint_q * (opq if opq is not None else self._v(other)))
        return Quantity(self._value * self._v(other))

    def __rmul__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint((opq if opq is not None else self._v(other)) * self._pint_q)
        return Quantity(self._v(other) * self._value)

    def __truediv__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint(self._pint_q / (opq if opq is not None else self._v(other)))
        return Quantity(self._value / self._v(other))

    def __rtruediv__(self, other: Any) -> Quantity[Any]:
        if self._pint_q is not None:
            opq = self._pq_of(other)
            return Quantity._from_pint((opq if opq is not None else self._v(other)) / self._pint_q)
        return Quantity(self._v(other) / self._value)

    def __floordiv__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value // self._v(other))

    def __pow__(self, exp: int | float, mod: None = None) -> Quantity[Any]:
        if self._pint_q is not None:
            return Quantity._from_pint(self._pint_q**exp)
        return Quantity(self._value**exp)

    def __neg__(self) -> Quantity[Any]:
        if self._pint_q is not None:
            return Quantity._from_pint(-self._pint_q)
        return Quantity(-self._value)

    def __pos__(self) -> Quantity[Any]:
        if self._pint_q is not None:
            return Quantity._from_pint(+self._pint_q)
        return Quantity(+self._value)

    def __abs__(self) -> Quantity[Any]:
        if self._pint_q is not None:
            return Quantity._from_pint(abs(self._pint_q))
        return Quantity(abs(self._value))

    # ------------------------------------------------------------------
    # NumPy integration — intercept ufuncs and array conversion so that
    # numpy operations on Quantity objects work correctly at runtime.
    # ------------------------------------------------------------------

    def __array__(self, dtype: Any = None) -> np.ndarray[Any, np.dtype[Any]]:
        try:
            import numpy as _np

            return _np.asarray(self._value, dtype=dtype)
        except ImportError:
            raise TypeError("numpy is required for array conversion") from None

    def __array_ufunc__(self, ufunc: Any, method: str, *inputs: Any, **kwargs: Any) -> Any:
        raw = [x._value if isinstance(x, Quantity) else x for x in inputs]
        result = getattr(ufunc, method)(*raw, **kwargs)
        if isinstance(result, tuple):
            return tuple(Quantity(r) for r in result)
        return Quantity(result)
