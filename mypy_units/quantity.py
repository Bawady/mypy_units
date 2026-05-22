from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    import numpy as np

_U_co = TypeVar("_U_co", bound=str, covariant=True)


class Quantity(float, Generic[_U_co]):
    """A numeric value carrying a static unit annotation.

    Subclasses ``float``: a ``Quantity`` IS a float at runtime.  The standard
    (non-escape-hatch) path has no overhead beyond a float-subclass allocation;
    all dimension tracking happens at static-analysis time via the mypy plugin.

    **Standard use**::

        d: meter = Quantity(10.0)
        v: meter_per_second = d / t   # plugin tracks dimension, runtime is float

    **Escape hatch** — pass a unit string to get pint backing::

        v: kilometer_per_hour = (Quantity(d, "m") / Quantity(t, "s")).to("km/h")
    """

    __slots__ = ()

    def __new__(
        cls,
        value: int | float | Quantity[Any] = 0,
        unit: str | None = None,
    ) -> Quantity[Any]:
        raw = float(value)
        if unit is not None:
            from mypy_units.dimension import _registry

            pq = _registry().Quantity(raw, unit)
            obj = float.__new__(_PintQuantity, pq.magnitude)
            obj._pint_q = pq  # type: ignore[attr-defined]
            return obj  # type: ignore[return-value]
        return float.__new__(cls, raw)

    def to(self, unit: str) -> Quantity[Any]:
        """Requires a pint-backed Quantity (created with Quantity(value, 'unit'))."""
        raise TypeError(
            "Quantity.to() is only available on unit-string Quantities. "
            "Create one with Quantity(value, 'unit') to enable pint-backed conversion."
        )

    # ------------------------------------------------------------------
    # Arithmetic — thin wrappers so the mypy plugin's method hooks fire
    # on Quantity operands and can track dimensions through expressions.
    # The runtime result is a plain float (no extra allocation).
    # ------------------------------------------------------------------

    def _v(self, other: Any) -> Any:
        return float(other) if isinstance(other, (int, float)) else other

    def __add__(self, other: Any) -> Quantity[Any]:
        return float.__add__(self, self._v(other))  # type: ignore[return-value]

    def __radd__(self, other: Any) -> Quantity[Any]:
        return float.__add__(self, self._v(other))  # type: ignore[return-value]

    def __sub__(self, other: Any) -> Quantity[Any]:
        return float.__sub__(self, self._v(other))  # type: ignore[return-value]

    def __rsub__(self, other: Any) -> Quantity[Any]:
        return float.__sub__(self._v(other), self)  # type: ignore[return-value]

    def __mul__(self, other: Any) -> Quantity[Any]:
        return float.__mul__(self, self._v(other))  # type: ignore[return-value]

    def __rmul__(self, other: Any) -> Quantity[Any]:
        return float.__mul__(self, self._v(other))  # type: ignore[return-value]

    def __truediv__(self, other: Any) -> Quantity[Any]:
        return float.__truediv__(self, self._v(other))  # type: ignore[return-value]

    def __rtruediv__(self, other: Any) -> Quantity[Any]:
        return float.__truediv__(self._v(other), self)  # type: ignore[return-value]

    def __floordiv__(self, other: Any) -> Quantity[Any]:
        return float.__floordiv__(self, self._v(other))  # type: ignore[return-value]

    def __pow__(self, exp: int | float, mod: None = None) -> Quantity[Any]:
        return float.__pow__(self, exp)  # type: ignore[return-value]

    def __neg__(self) -> Quantity[Any]:
        return float.__neg__(self)  # type: ignore[return-value]

    def __pos__(self) -> Quantity[Any]:
        return float.__pos__(self)  # type: ignore[return-value]

    def __abs__(self) -> Quantity[Any]:
        return float.__abs__(self)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # NumPy integration
    # ------------------------------------------------------------------

    def __array__(self, dtype: Any = None) -> np.ndarray[Any, np.dtype[Any]]:
        try:
            import numpy as _np

            return _np.asarray(float(self), dtype=dtype)
        except ImportError:
            raise TypeError("numpy is required for array conversion") from None

    def __array_ufunc__(self, ufunc: Any, method: str, *inputs: Any, **kwargs: Any) -> Any:
        import numpy as _np

        raw = [float(x) if isinstance(x, Quantity) else x for x in inputs]
        result = getattr(ufunc, method)(*raw, **kwargs)

        def _wrap(r: Any) -> Any:
            if isinstance(r, _np.ndarray):
                from mypy_units.array_quantity import QuantityArray

                return QuantityArray(r)
            return Quantity(r)

        if isinstance(result, tuple):
            return tuple(_wrap(r) for r in result)
        return _wrap(result)


class _PintQuantity(Quantity[Any]):
    """Pint-backed Quantity returned by ``Quantity(value, 'unit_str')``.

    Propagates pint backing through arithmetic so that ``.to()`` can be
    called on any intermediate result in an escape-hatch expression chain.
    """

    __slots__ = ("_pint_q",)
    _pint_q: Any

    def to(self, unit: str) -> Quantity[Any]:
        converted = self._pint_q.to(unit)
        return float.__new__(Quantity, converted.magnitude)

    def __repr__(self) -> str:
        return f"Quantity({float(self)!r}, {str(self._pint_q.units)!r})"

    @classmethod
    def _from_pint(cls, pq: Any) -> _PintQuantity:
        obj = float.__new__(cls, pq.magnitude)
        obj._pint_q = pq
        return obj

    def __add__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint(self._pint_q + (opq if opq is not None else float(other)))  # type: ignore[return-value]

    def __radd__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint((opq if opq is not None else float(other)) + self._pint_q)  # type: ignore[return-value]

    def __sub__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint(self._pint_q - (opq if opq is not None else float(other)))  # type: ignore[return-value]

    def __rsub__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint((opq if opq is not None else float(other)) - self._pint_q)  # type: ignore[return-value]

    def __mul__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint(self._pint_q * (opq if opq is not None else float(other)))  # type: ignore[return-value]

    def __rmul__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint((opq if opq is not None else float(other)) * self._pint_q)  # type: ignore[return-value]

    def __truediv__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint(self._pint_q / (opq if opq is not None else float(other)))  # type: ignore[return-value]

    def __rtruediv__(self, other: Any) -> Quantity[Any]:
        opq = getattr(other, "_pint_q", None)
        return _PintQuantity._from_pint((opq if opq is not None else float(other)) / self._pint_q)  # type: ignore[return-value]

    def __pow__(self, exp: int | float, mod: None = None) -> Quantity[Any]:
        return _PintQuantity._from_pint(self._pint_q**exp)  # type: ignore[return-value]

    def __neg__(self) -> Quantity[Any]:
        return _PintQuantity._from_pint(-self._pint_q)  # type: ignore[return-value]

    def __pos__(self) -> Quantity[Any]:
        return _PintQuantity._from_pint(+self._pint_q)  # type: ignore[return-value]

    def __abs__(self) -> Quantity[Any]:
        return _PintQuantity._from_pint(abs(self._pint_q))  # type: ignore[return-value]
