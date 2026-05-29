from __future__ import annotations

from typing import Any, Generic, TypeVar

_U_co = TypeVar("_U_co", bound=str, covariant=True)


class Quantity(float, Generic[_U_co]):
    """Unit annotation carrier for the mypy plugin.

    At runtime ``Quantity(value)`` returns a plain ``float`` — no subclass,
    no overhead.  All dimension tracking happens at static-analysis time via
    the mypy plugin.

    **Standard use**::

        d: meter = Quantity(10.0)      # type(d) is float
        v: meter_per_second = d / t   # plugin tracks dimension, runtime is float

    **Escape hatch** — pass a unit string to get pint backing::

        v: kilometer_per_hour = (Quantity(d, "m") / Quantity(t, "s")).to("km/h")
    """

    __slots__ = ()

    def __new__(
        cls,
        value: int | float = 0,
        unit: str | None = None,
    ) -> Quantity[Any]:
        raw = float(value)
        if unit is not None:
            from mypy_units.dimension import _registry

            pq = _registry().Quantity(raw, unit)
            obj = float.__new__(_PintQuantity, pq.magnitude)
            obj._pint_q = pq  # type: ignore[attr-defined]
            return obj  # type: ignore[return-value]
        return raw  # type: ignore[return-value]

    def to(self, unit: str) -> Quantity[Any]:
        """Only reachable via the mypy static type; runtime object is a plain float."""
        raise TypeError(
            "Quantity.to() is only available on unit-string Quantities. "
            "Create one with Quantity(value, 'unit') to enable pint-backed conversion."
        )

    # ------------------------------------------------------------------
    # Arithmetic method declarations — kept as mypy plugin hook attachment
    # points so hooks registered on Quantity.__truediv__ etc. fire when the
    # static type of an operand is Quantity[...].  Bodies are unreachable at
    # runtime: Quantity() returns a plain float, so Python always dispatches
    # to float's C-level arithmetic, never to these methods.
    # ------------------------------------------------------------------

    def __add__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __radd__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __sub__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __rsub__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __mul__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __rmul__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __truediv__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __rtruediv__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __floordiv__(self, other: Any) -> Quantity[Any]:
        raise NotImplementedError

    def __pow__(self, exp: int | float, mod: None = None) -> Quantity[Any]:
        raise NotImplementedError

    def __neg__(self) -> Quantity[Any]:
        raise NotImplementedError

    def __pos__(self) -> Quantity[Any]:
        raise NotImplementedError

    def __abs__(self) -> Quantity[Any]:
        raise NotImplementedError


class _PintQuantity(Quantity[Any]):
    """Pint-backed Quantity returned by ``Quantity(value, 'unit_str')``.

    Propagates pint backing through arithmetic so that ``.to()`` can be
    called on any intermediate result in an escape-hatch expression chain.
    """

    __slots__ = ("_pint_q",)
    _pint_q: Any

    def to(self, unit: str) -> Quantity[Any]:
        converted = self._pint_q.to(unit)
        return float(converted.magnitude)  # type: ignore[return-value]

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
