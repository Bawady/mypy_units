"""numpy array quantities with physical unit annotations."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

_Q_co = TypeVar("_Q_co", covariant=True)


class QuantityArray(Generic[_Q_co]):
    """Unit annotation carrier for arrays.

    At runtime ``QuantityArray(value)`` returns the underlying array
    **unchanged** — a plain ``numpy.ndarray`` (or any array that already
    carries a ``dtype``, such as a JAX array or a JAX tracer).  No wrapper
    object is created; all dimension tracking happens at static-analysis
    time via the mypy plugin.

    The type parameter is a unit alias (e.g. ``meter``, ``second``)::

        d: Array[meter] = QuantityArray(np.array([1.0, 2.0, 3.0]))
        # type(d) is numpy.ndarray

    Transparency makes the value directly consumable by accelerators such as
    JAX: an array passed in is returned as-is (never copied or concretized),
    so it can flow through ``jax.jit`` traces untouched.

    The underlying dtype must be numeric (floating or integer); a
    :class:`TypeError` is raised on construction otherwise.  The dtype is
    inspected without materializing the array, so the check is safe on JAX
    tracers.
    """

    __slots__ = ()

    def __new__(cls, value: Any) -> QuantityArray[Any]:
        import numpy as _np

        # Leave anything that already exposes a dtype untouched (ndarray,
        # JAX array, JAX tracer).  Only promote plain sequences/scalars.
        arr = value if hasattr(value, "dtype") else _np.asarray(value)
        if not _np.issubdtype(arr.dtype, _np.number):
            raise TypeError(f"QuantityArray dtype must be numeric (float or int), got {arr.dtype}")
        return arr  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Arithmetic method declarations — kept as mypy plugin hook attachment
    # points so hooks registered on QuantityArray.__truediv__ etc. fire when
    # the static type of an operand is QuantityArray[...].  Bodies are
    # unreachable at runtime: QuantityArray() returns a plain array, so Python
    # always dispatches to the array's own arithmetic, never to these methods.
    # ------------------------------------------------------------------

    def __add__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __radd__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __sub__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __rsub__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __mul__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __rmul__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __truediv__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __rtruediv__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __floordiv__(self, other: Any) -> QuantityArray[Any]:
        raise NotImplementedError

    def __pow__(self, exp: int | float, mod: None = None) -> QuantityArray[Any]:
        raise NotImplementedError

    def __neg__(self) -> QuantityArray[Any]:
        raise NotImplementedError

    def __pos__(self) -> QuantityArray[Any]:
        raise NotImplementedError

    def __abs__(self) -> QuantityArray[Any]:
        raise NotImplementedError
