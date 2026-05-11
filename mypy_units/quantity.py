from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    import numpy as np

_U_co = TypeVar("_U_co", bound=str, covariant=True)


class Quantity(Generic[_U_co]):
    """A numeric value (scalar or numpy array) carrying a static unit annotation.

    The type parameter is a Pint dimensionality string (e.g. ``"[length]"``).

    **Construction**::

        d: kilometer = Quantity(10)
        d_arr: kilometer = Quantity(np.array([1.0, 2.0, 3.0]))

    **Arithmetic** — all standard operations are supported and propagate to the
    wrapped value (float or numpy array).  The *static* type of arithmetic
    results is tracked by the mypy plugin via method hooks.
    """

    _value: Any

    def __init__(self, value: int | float | complex = 0) -> None:
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    def __repr__(self) -> str:
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
    # ------------------------------------------------------------------

    def _v(self, other: Any) -> Any:
        return other._value if isinstance(other, Quantity) else other

    def __add__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value + self._v(other))

    def __radd__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._v(other) + self._value)

    def __sub__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value - self._v(other))

    def __rsub__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._v(other) - self._value)

    def __mul__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value * self._v(other))

    def __rmul__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._v(other) * self._value)

    def __truediv__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value / self._v(other))

    def __rtruediv__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._v(other) / self._value)

    def __floordiv__(self, other: Any) -> Quantity[Any]:
        return Quantity(self._value // self._v(other))

    def __pow__(self, exp: int | float, mod: None = None) -> Quantity[Any]:
        return Quantity(self._value ** exp)

    def __neg__(self) -> Quantity[Any]:
        return Quantity(-self._value)

    def __pos__(self) -> Quantity[Any]:
        return Quantity(+self._value)

    def __abs__(self) -> Quantity[Any]:
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
