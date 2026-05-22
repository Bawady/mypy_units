"""numpy array quantities with physical unit annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    import numpy as np

_Q_co = TypeVar("_Q_co", covariant=True)


class QuantityArray(Generic[_Q_co]):
    """numpy array annotated with a physical unit.

    The type parameter is a unit alias (e.g. ``meter``, ``second``)::

        d: Array[meter] = QuantityArray(np.array([1.0, 2.0, 3.0]))

    The underlying ndarray dtype must be numeric (floating or integer);
    a :class:`TypeError` is raised on construction otherwise.
    """

    _value: Any

    def __init__(self, value: Any) -> None:
        import numpy as _np

        arr = _np.asarray(value)
        if not _np.issubdtype(arr.dtype, _np.number):
            raise TypeError(f"QuantityArray dtype must be numeric (float or int), got {arr.dtype}")
        self._value = arr

    @property
    def value(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        return f"QuantityArray({self._value!r})"

    def _v(self, other: Any) -> Any:
        return other._value if isinstance(other, QuantityArray) else other

    # ------------------------------------------------------------------
    # Arithmetic — delegates to the wrapped ndarray; plugin hooks track
    # the dimension of each result at static analysis time.
    # ------------------------------------------------------------------

    def __add__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._value + self._v(other))

    def __radd__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._v(other) + self._value)

    def __sub__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._value - self._v(other))

    def __rsub__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._v(other) - self._value)

    def __mul__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._value * self._v(other))

    def __rmul__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._v(other) * self._value)

    def __truediv__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._value / self._v(other))

    def __rtruediv__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._v(other) / self._value)

    def __floordiv__(self, other: Any) -> QuantityArray[Any]:
        return QuantityArray(self._value // self._v(other))

    def __pow__(self, exp: int | float, mod: None = None) -> QuantityArray[Any]:
        return QuantityArray(self._value**exp)

    def __neg__(self) -> QuantityArray[Any]:
        return QuantityArray(-self._value)

    def __pos__(self) -> QuantityArray[Any]:
        return QuantityArray(+self._value)

    def __abs__(self) -> QuantityArray[Any]:
        return QuantityArray(abs(self._value))

    # ------------------------------------------------------------------
    # NumPy integration — intercept ufuncs so numpy operations on
    # QuantityArray objects work correctly at runtime.
    # ------------------------------------------------------------------

    def __array__(self, dtype: Any = None) -> np.ndarray[Any, np.dtype[Any]]:
        import numpy as _np

        return _np.asarray(self._value, dtype=dtype)

    def __array_ufunc__(self, ufunc: Any, method: str, *inputs: Any, **kwargs: Any) -> Any:
        raw = [x._value if isinstance(x, QuantityArray) else x for x in inputs]
        result = getattr(ufunc, method)(*raw, **kwargs)
        if isinstance(result, tuple):
            return tuple(QuantityArray(r) for r in result)
        return QuantityArray(result)
