"""Tests for mypy_units plugin — invokes real mypy on inline fixtures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


def no_error(output: str) -> None:
    assert "Dimension mismatch" not in output, f"Unexpected error:\n{output}"
    assert "Unit mismatch" not in output, f"Unexpected error:\n{output}"
    unexpected = [
        line for line in output.splitlines() if "error:" in line and "[empty-body]" not in line
    ]
    assert not unexpected, "Unexpected mypy error:\n" + "\n".join(unexpected)


def has_mismatch(output: str, arg: str | None = None) -> None:
    assert "Dimension mismatch" in output or "Unit mismatch" in output, (
        f"Expected dimension or unit mismatch, got:\n{output}"
    )
    if arg:
        assert arg in output, f"Expected mismatch on '{arg}', got:\n{output}"


# ---------------------------------------------------------------------------
# 1. Unit→Unit same unit — exact match passes
# ---------------------------------------------------------------------------
def test_unit_to_unit_exact_match(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: meter) -> float: ...

        x: meter
        travel(x)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 1b. Unit→Unit same dimension but different scale — flagged as unit mismatch
# ---------------------------------------------------------------------------
def test_unit_to_unit_scale_mismatch(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: meter) -> float: ...

        x: kilometer
        travel(x)
    """)
    has_mismatch(out, "d")


# ---------------------------------------------------------------------------
# 2. Unit→Unit different dimension (second passed where meter expected)
# ---------------------------------------------------------------------------
def test_unit_to_unit_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: meter) -> float: ...

        t: second
        travel(t)
    """)
    has_mismatch(out, "d")


# ---------------------------------------------------------------------------
# 3. Compound unit from arithmetic matches declared return type
# ---------------------------------------------------------------------------
def test_compound_unit_arithmetic_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.units import joule

        def kinetic_energy(m: kilogram, v: meter_per_second) -> joule:
            return m * v * v
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 4. Same dimension, different scale — all three rejected
# ---------------------------------------------------------------------------
def test_same_dim_different_scale_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.units import centimeter, millimeter

        def go(d: meter) -> float: ...

        a: kilometer
        b: centimeter
        c: millimeter
        go(a)
        go(b)
        go(c)
    """)
    assert out.count("Unit mismatch") == 3, (
        f"Expected 3 unit-mismatch errors (km, cm, mm), got:\n{out}"
    )


# ---------------------------------------------------------------------------
# 5. Compound wrong dimension is rejected at call site
# ---------------------------------------------------------------------------
def test_compound_unit_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.units import joule, newton

        def work(f: newton, d: meter) -> joule: ...

        f: newton
        t: second   # [time] ≠ [length]
        work(f, t)
    """)
    has_mismatch(out, "d")


# ---------------------------------------------------------------------------
# 6. Plain float argument — escape hatch, no error
# ---------------------------------------------------------------------------
def test_plain_float_escape_hatch(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def go(d: meter) -> float: ...

        x: float = 1.0
        go(x)  # type: ignore[arg-type]
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 7. Multi-parameter function — scale mismatch and dimension mismatch both caught
# ---------------------------------------------------------------------------
def test_multi_param_both_errors(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: meter, time: second) -> float: ...

        d: kilometer    # same dimension, wrong scale
        t: kilogram     # wrong dimension entirely

        speed(d, t)
    """)
    has_mismatch(out, "distance")
    has_mismatch(out, "time")


# ---------------------------------------------------------------------------
# 8. Invalid unit string — plugin skips gracefully, no crash
# ---------------------------------------------------------------------------
def test_invalid_unit_string(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def go(d: Quantity[Literal["florgles"]]) -> float: ...

        x: Quantity[Literal["florgles"]]
        go(x)
    """)
    assert "Internal error" not in out, f"Plugin crashed:\n{out}"
    assert "Dimension mismatch" not in out, f"Unexpected mismatch:\n{out}"


# ---------------------------------------------------------------------------
# 9. Dimensionless: degree has a different scale than radian — flagged
# ---------------------------------------------------------------------------
def test_dimensionless_scale_mismatch(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.units import degree

        def rotate(angle: radian) -> float: ...

        d: degree
        rotate(d)
    """)
    has_mismatch(out, "angle")


# ---------------------------------------------------------------------------
# 10. Return type propagates through call chain
# ---------------------------------------------------------------------------
def test_return_type_propagates(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: kilometer, time: second) -> meter_per_second: ...

        def accel(v: meter_per_second, t: second) -> meter_per_second_squared: ...

        d: kilometer
        t: second

        v = speed(d, t)    # v is inferred as meter_per_second
        accel(v, t)        # plugin sees meter_per_second — OK
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 11. Wrong unit in a chained call detected
# ---------------------------------------------------------------------------
def test_return_type_chain_wrong(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: meter, time: second) -> meter_per_second: ...

        def expects_length(x: meter) -> float: ...

        d: meter
        t: second

        v = speed(d, t)      # v: meter_per_second
        expects_length(v)    # error: [length] ≠ [length]/[time]
    """)
    has_mismatch(out, "x")


# ---------------------------------------------------------------------------
# 12. Body arithmetic — dimensionally and scaling correct, no error
# ---------------------------------------------------------------------------
def test_body_arith_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: meter, time: second) -> meter_per_second:
            return distance / time
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 13. Body arithmetic — dimensionally wrong, mypy catches return-value mismatch
# ---------------------------------------------------------------------------
def test_body_arith_wrong(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: kilometer, time: second) -> meter_per_second:
            tmp = distance * time     # [length] * [time]
            return tmp / time         # [length], not [length]/[time]
    """)
    assert "error:" in out, f"Expected a mypy error, got:\n{out}"
    assert "return-value" in out or "Incompatible return value" in out, (
        f"Expected a return-value type error, got:\n{out}"
    )


# ---------------------------------------------------------------------------
# 14. Array[unit] same dimension — passes dimension check
# ---------------------------------------------------------------------------
def test_numpy_array_same_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Array[kilometer]) -> float: ...

        d_arr: Array[kilometer] = QuantityArray(np.array([1.0, 2.0, 3.0]))
        travel(d_arr)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 15. Array[unit] wrong dimension — caught
# ---------------------------------------------------------------------------
def test_numpy_array_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Array[kilometer]) -> float: ...

        t_arr: Array[second] = QuantityArray(np.array([1.0, 2.0]))
        travel(t_arr)
    """)
    has_mismatch(out, "d")


# ---------------------------------------------------------------------------
# 16. Array body arithmetic — dimension and scaling tracked through array ops
# ---------------------------------------------------------------------------
def test_numpy_body_arith(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: Array[meter], time: Array[second]) -> Array[meter_per_second]:
            return distance / time
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 25. Quantity rejects numpy ndarray — scalar constructor is float-only
# ---------------------------------------------------------------------------
def test_quantity_rejects_ndarray(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        x = Quantity(np.array([1.0, 2.0]))
    """)
    assert "error:" in out, f"Expected [arg-type] error for ndarray argument:\n{out}"


# ---------------------------------------------------------------------------
# 26. Array * scalar → Array of correct dimension (body arithmetic)
# ---------------------------------------------------------------------------
def test_array_times_scalar_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def distance_covered(v: Array[meter_per_second], t: second) -> Array[meter]:
            return v * t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 27. scalar * Array → Array of correct dimension (reversed operands)
# ---------------------------------------------------------------------------
def test_scalar_times_array_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def distance_covered(t: second, v: Array[meter_per_second]) -> Array[meter]:
            return t * v
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 28. Array * scalar wrong return dimension — caught as return-value error
# ---------------------------------------------------------------------------
def test_array_times_scalar_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(v: Array[meter_per_second], t: second) -> Array[meter_per_second_squared]:
            return v * t   # [length], not [length]/[time]**2
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 29. Scalar passed to Array parameter — type error, not dimension mismatch
# ---------------------------------------------------------------------------
def test_scalar_to_array_param_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(d: Array[meter]) -> float: ...

        d_scalar: meter = Quantity(5.0)
        func(d_scalar)
    """)
    assert "error:" in out, f"Expected type error:\n{out}"
    assert "Dimension mismatch" not in out, f"Expected type error, not dim mismatch:\n{out}"


# ---------------------------------------------------------------------------
# 30. Array passed to scalar parameter — type error, not dimension mismatch
# ---------------------------------------------------------------------------
def test_array_to_scalar_param_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(d: meter) -> float: ...

        d_arr: Array[meter] = QuantityArray(np.array([1.0, 2.0]))
        func(d_arr)
    """)
    assert "error:" in out, f"Expected type error:\n{out}"
    assert "Dimension mismatch" not in out, f"Expected type error, not dim mismatch:\n{out}"


# ---------------------------------------------------------------------------
# 31. Array with same-dimension but different scale — rejected
# ---------------------------------------------------------------------------
def test_array_different_scale_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(d: Array[meter]) -> float: ...

        d_km: Array[kilometer] = QuantityArray(np.array([1.0, 2.0]))
        func(d_km)
    """)
    has_mismatch(out, "d")


# ---------------------------------------------------------------------------
# 32. Function with Array and scalar params — correct call, no error
# ---------------------------------------------------------------------------
def test_mixed_params_call_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(arr: Array[meter_per_second], t: second) -> Array[meter]:
            return arr * t

        v_arr: Array[meter_per_second] = QuantityArray(np.array([1.0, 2.0]))
        t_val: second = Quantity(2.0)
        func(v_arr, t_val)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 33. Function with Array and scalar params — wrong scalar dim at call site
# ---------------------------------------------------------------------------
def test_mixed_params_call_wrong_scalar_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(arr: Array[meter_per_second], t: second) -> Array[meter]:
            return arr * t

        v_arr: Array[meter_per_second] = QuantityArray(np.array([1.0, 2.0]))
        m_val: kilogram = Quantity(2.0)
        func(v_arr, m_val)
    """)
    has_mismatch(out, "t")


# ---------------------------------------------------------------------------
# 34. Function with Array and scalar params — wrong array dim at call site
# ---------------------------------------------------------------------------
def test_mixed_params_call_wrong_array_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(arr: Array[meter_per_second], t: second) -> Array[meter]:
            return arr * t

        v_arr: Array[meter] = QuantityArray(np.array([1.0, 2.0]))   # wrong dim
        t_val: second = Quantity(2.0)
        func(v_arr, t_val)
    """)
    has_mismatch(out, "arr")


# ---------------------------------------------------------------------------
# Runtime: QuantityArray dtype enforcement (no mypy fixture needed)
# ---------------------------------------------------------------------------


def test_array_rejects_nonnumeric_dtype() -> None:
    import numpy as np
    import pytest

    from mypy_units import QuantityArray

    with pytest.raises(TypeError, match="numeric"):
        QuantityArray(np.array(["hello", "world"]))


def test_array_accepts_float64_dtype() -> None:
    import numpy as np

    from mypy_units import QuantityArray

    # QuantityArray() returns the array unchanged at runtime (a plain ndarray).
    arr: Any = QuantityArray(np.array([1.0, 2.0, 3.0]))
    assert arr.dtype == np.float64


def test_array_accepts_integer_dtype() -> None:
    import numpy as np

    from mypy_units import QuantityArray

    arr: Any = QuantityArray(np.array([1, 2, 3]))
    assert np.issubdtype(arr.dtype, np.integer)


# ---------------------------------------------------------------------------
# Runtime: QuantityArray is transparent — returns the underlying array
# unchanged, which keeps it usable inside jax.jit / jax.grad traces.
# ---------------------------------------------------------------------------


def test_array_is_transparent_returns_input_unchanged() -> None:
    import numpy as np

    from mypy_units import QuantityArray

    src = np.array([1.0, 2.0, 3.0])
    # An object already carrying a dtype is returned as-is (no copy, no wrapper).
    assert QuantityArray(src) is src


def test_jax_array_passthrough_identity() -> None:
    import pytest

    jnp = pytest.importorskip("jax.numpy")

    from mypy_units import QuantityArray

    x = jnp.array([1.0, 2.0, 3.0])
    # JAX array is returned unchanged (never concretized to numpy).
    assert QuantityArray(x) is x


def test_jax_jit_constructs_quantityarray_on_tracer() -> None:
    import pytest

    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    import numpy as np

    from mypy_units import QuantityArray

    @jax.jit
    def speed(d: Any, t: Any) -> Any:
        # QuantityArray() is called on JAX tracers during the trace; it must
        # return them unchanged so division stays a traced operation.
        return QuantityArray(d) / QuantityArray(t)

    out = speed(jnp.array([10.0, 20.0]), jnp.array([2.0, 5.0]))
    np.testing.assert_allclose(np.asarray(out), [5.0, 4.0])


def test_jax_grad_through_quantityarray() -> None:
    import pytest

    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    import numpy as np

    from mypy_units import QuantityArray

    def speed0(d: Any) -> Any:
        v: Any = QuantityArray(d) / QuantityArray(jnp.array([2.0, 5.0]))
        return v[0]

    g = jax.grad(speed0)(jnp.array([10.0, 20.0]))
    np.testing.assert_allclose(np.asarray(g), [0.5, 0.0])


# ---------------------------------------------------------------------------
# 17. power(t, 2) tracked — result is [time]**2
# ---------------------------------------------------------------------------
def test_numpy_power_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def accel(d: meter, t: second) -> meter_per_second_squared:
            return d / power(t, 2)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 18. power(t, 2) with wrong result dim — caught as return-value error
# ---------------------------------------------------------------------------
def test_numpy_power_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> meter_per_second:
            return d / power(t, 2)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 19. sqrt of square_meter gives meter
# ---------------------------------------------------------------------------
def test_numpy_sqrt_area_to_length(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def side(a: square_meter) -> meter:
            return sqrt(a)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 20. sqrt of square_meter does not give meter_per_second — caught
# ---------------------------------------------------------------------------
def test_numpy_sqrt_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(a: square_meter) -> meter_per_second:
            return sqrt(a)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 21. np.power directly — dimension tracked through ufunc hook
# ---------------------------------------------------------------------------
def test_np_power_direct_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def accel(d: meter, t: second) -> meter_per_second_squared:
            return d / np.power(t, 2)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 22. np.power directly — wrong dimension caught
# ---------------------------------------------------------------------------
def test_np_power_direct_wrong(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> meter_per_second:
            return d / np.power(t, 2)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 23. np.sqrt directly — sqrt of square_meter gives meter
# ---------------------------------------------------------------------------
def test_np_sqrt_direct_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def side(a: square_meter) -> meter:
            return np.sqrt(a)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 24. np.sqrt directly — wrong return dimension caught
# ---------------------------------------------------------------------------
def test_np_sqrt_direct_wrong(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(a: square_meter) -> meter_per_second:
            return np.sqrt(a)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 24a. max(array) reduces to a scalar of the same unit
# ---------------------------------------------------------------------------
def test_numpy_max_array_to_scalar(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.numpy import max as amax
        def hottest(speeds: Array[meter_per_second]) -> meter_per_second:
            return amax(speeds)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 24b. min(array) reduces to a scalar of the same unit
# ---------------------------------------------------------------------------
def test_numpy_min_array_to_scalar(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.numpy import min as amin
        def slowest(speeds: Array[meter_per_second]) -> meter_per_second:
            return amin(speeds)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 24c. max(array) with a wrong-unit return annotation — caught
# ---------------------------------------------------------------------------
def test_numpy_max_wrong_unit(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.numpy import max as amax
        def bad(speeds: Array[meter_per_second]) -> second:
            return amax(speeds)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 24d. max() result is a scalar Quantity, not a QuantityArray
# ---------------------------------------------------------------------------
def test_numpy_max_result_is_scalar(mypy_fixture: Callable[[str], str]) -> None:
    # Returning the scalar where an Array is expected must be rejected: the
    # reduction collapses the array dimension.
    out = mypy_fixture("""
        from mypy_units.numpy import max as amax
        def bad(speeds: Array[meter_per_second]) -> Array[meter_per_second]:
            return amax(speeds)
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 24e. max() tracks a compound unit built by arithmetic
# ---------------------------------------------------------------------------
def test_numpy_max_compound_unit(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.numpy import max as amax
        def peak(d: meter, ts: QuantityArray[second]) -> meter_per_second:
            return amax(d / ts)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 35. ScaleFactor: 3.6 * (m/s) → km/h — accepted
# ---------------------------------------------------------------------------
def test_conversion_factor_mul_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_in_kmh(d: meter, t: second) -> kilometer_per_hour:
            return ScaleFactor(3.6) * d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 36. ScaleFactor: wrong factor — return-value error
# ---------------------------------------------------------------------------
def test_conversion_factor_wrong_value(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> kilometer_per_hour:
            return ScaleFactor(1) * d / t   # 1 m/s ≠ km/h scale
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 37. ScaleFactor: (second) / ScaleFactor(3600) → hour — accepted
# ---------------------------------------------------------------------------
def test_conversion_factor_div_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel_time_hours(d: meter, v: meter_per_second) -> hour:
            return (d / v) / ScaleFactor(3600)
    """)
    no_error(out)


# ===========================================================================
# ScaleFactor: comprehensive positive / negative test suite
# ===========================================================================


# ---------------------------------------------------------------------------
# 38. CF necessary but missing (no scalar at all) — return-value error
# ---------------------------------------------------------------------------
def test_cf_missing_no_scalar(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_wrong(d: meter, t: second) -> kilometer_per_hour:
            return d / t   # m/s ≠ km/h, no conversion
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 39. CF necessary but missing (plain float used, not wrapped) — return-value error
# ---------------------------------------------------------------------------
def test_cf_missing_plain_float(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_wrong(d: meter, t: second) -> kilometer_per_hour:
            return 3.6 * d / t   # plain scalar: no type effect, still m/s
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 40. CF necessary but wrong value — return-value error
# ---------------------------------------------------------------------------
def test_cf_necessary_wrong_value(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_wrong(d: meter, t: second) -> kilometer_per_hour:
            return ScaleFactor(2) * d / t   # 2 ≠ 3.6
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 41. CF(1) on already-correct expression — type is preserved, no error
# ---------------------------------------------------------------------------
def test_cf_unity_preserves_correct_type(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: meter, t: second) -> meter_per_second:
            return ScaleFactor(1) * d / t   # ScaleFactor(1): scale / 1 = unchanged
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 42. CF(1) does NOT fix a scale-wrong expression — still fails
# ---------------------------------------------------------------------------
def test_cf_unity_does_not_fix_wrong_scale(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_wrong(d: meter, t: second) -> kilometer_per_hour:
            return ScaleFactor(1) * d / t   # m/s ≠ km/h regardless of CF(1)
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 43. CF in a variable assignment — correct factor accepted
# ---------------------------------------------------------------------------
def test_cf_assignment_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d: meter = Quantity(100.0)
        t: second = Quantity(50.0)
        v: kilometer_per_hour = ScaleFactor(3.6) * d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 44. CF in a variable assignment — wrong factor rejected
# ---------------------------------------------------------------------------
def test_cf_assignment_wrong_factor(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d: meter = Quantity(100.0)
        t: second = Quantity(50.0)
        v: kilometer_per_hour = ScaleFactor(2) * d / t   # 2 ≠ 3.6
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 45. Assign meter Quantity to kilometer via division by ScaleFactor(1000)
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_div(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_m: meter = Quantity(1000.0)
        d_km: kilometer = d_m / ScaleFactor(1000)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 46. Assign kilometer Quantity to meter via multiplication by ScaleFactor(1000)
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_mul(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_km: kilometer = Quantity(1.0)
        d_m: meter = d_km * ScaleFactor(1000)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 47. Same-dimension unit reassignment with wrong CF value — rejected
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_wrong_factor(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_m: meter = Quantity(1000.0)
        d_km: kilometer = d_m / ScaleFactor(100)   # 100 ≠ 1000
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 47a. ScaleFactor with a folded literal-arithmetic argument — accepted
# ---------------------------------------------------------------------------
def test_cf_folds_literal_arithmetic(mypy_fixture: Callable[[str], str]) -> None:
    # km/h has scale 5/18 m/s; 1000/3600 == 5/18, so the value is rescaled to
    # plain meter/second.  The deliberate, self-documenting 1000 / 3600 form
    # must be statically folded rather than dropped.
    out = mypy_fixture("""
        def to_ms(v: kilometer_per_hour) -> meter_per_second:
            return ScaleFactor(1000 / 3600) * v
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 47b. ScaleFactor with a folded literal that is WRONG — still rejected
# ---------------------------------------------------------------------------
def test_cf_folds_literal_arithmetic_wrong(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def to_ms(v: kilometer_per_hour) -> meter_per_second:
            return ScaleFactor(1000 / 360) * v   # 10x off
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 47c. ScaleFactor(<variable>) cannot be tracked — flagged (fail closed)
# ---------------------------------------------------------------------------
def test_cf_non_literal_variable_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        k = 1000.0
        def to_km(d: meter) -> kilometer:
            return d / ScaleFactor(k)
    """)
    assert "ScaleFactor(...) requires a statically evaluable numeric literal" in out


# ---------------------------------------------------------------------------
# 47d. ScaleFactor(<call result>) cannot be tracked — flagged (fail closed)
# ---------------------------------------------------------------------------
def test_cf_non_literal_call_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def factor() -> float: ...
        def to_km(d: meter) -> kilometer:
            return d / ScaleFactor(factor())
    """)
    assert "ScaleFactor(...) requires a statically evaluable numeric literal" in out


# ---------------------------------------------------------------------------
# 47e. ScaleFactor(0) — undefined conversion, flagged (fail closed)
# ---------------------------------------------------------------------------
def test_cf_zero_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def to_km(d: meter) -> kilometer:
            return d / ScaleFactor(0)
    """)
    assert "ScaleFactor(...) requires a statically evaluable numeric literal" in out


# ===========================================================================
# ScaleFactor: offset conversions (temperature, etc.)
# ===========================================================================


# ===========================================================================
# Scalar["..."] and Array["..."] expression tests
# ===========================================================================


# ---------------------------------------------------------------------------
# 48. Scalar["meter"] as annotation — same as meter, should pass
# ---------------------------------------------------------------------------
def test_scalar_simple_annotation(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Scalar["meter"]) -> float: ...

        x: meter
        travel(x)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 49. Scalar["km/h"] as return type of d/t with d: kilometer, t: hour — pass
# ---------------------------------------------------------------------------
def test_scalar_compound_return_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: kilometer, t: hour) -> Scalar[Literal["km/h"]]:
            return d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 49b. Scalar["kilometer_per_hour"] — underscore alias also works
# ---------------------------------------------------------------------------
def test_scalar_compound_underscore_name(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: kilometer, t: hour) -> Scalar["kilometer_per_hour"]:
            return d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 50. Scalar[Literal["km/h"]] as return type with wrong scale — fail
# ---------------------------------------------------------------------------
def test_scalar_compound_return_wrong_scale(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: meter, t: second) -> Scalar[Literal["km/h"]]:
            return d / t  # m/s ≠ km/h scale
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 51. Scalar[Literal["m/s**2"]] as return type of F/m with newton-equivalent F
# ---------------------------------------------------------------------------
def test_scalar_power_expression(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def accel(
            F: Scalar[Literal["kg*m/s**2"]], m: kilogram
        ) -> Scalar[Literal["m/s**2"]]:
            return F / m
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 52. Scalar[Literal["kg*m/s**2"]] as return type of m*a
# ---------------------------------------------------------------------------
def test_scalar_nested_expression(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def force(
            m: kilogram, a: Scalar[Literal["m/s**2"]]
        ) -> Scalar[Literal["kg*m/s**2"]]:
            return m * a
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 53. Module-level alias using Literal syntax — pass
# ---------------------------------------------------------------------------
def test_scalar_module_alias(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        kmh = Scalar[Literal["km/h"]]

        def speed(d: kilometer, t: hour) -> kmh:
            return d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 54. Scalar[Literal["km/h"]] where actual return is m/s — fail
# ---------------------------------------------------------------------------
def test_scalar_wrong_scale(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: meter, t: second) -> Scalar[Literal["km/h"]]:
            return d / t  # returns m/s, not km/h
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 55. ScaleFactor works inside a Scalar[Literal["..."]]-annotated function body
# ---------------------------------------------------------------------------
def test_scalar_with_scalefactor(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_in_kmh(d: meter, t: second) -> Scalar[Literal["km/h"]]:
            return ScaleFactor(3.6) * d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 56. Array["m/s"] as annotation — should pass
# ---------------------------------------------------------------------------
def test_array_simple_annotation(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Array["meter"]) -> float: ...

        x: Array[meter]
        travel(x)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 57. Scalar where Array expected — type error
# ---------------------------------------------------------------------------
def test_scalar_where_array_expected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Array["meter"]) -> float: ...

        x: meter
        travel(x)
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 58. Array where Scalar expected — type error
# ---------------------------------------------------------------------------
def test_array_where_scalar_expected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Scalar["meter"]) -> float: ...

        x: Array[meter]
        travel(x)
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 59. Invalid pint string — should produce error or be treated as Any
# ---------------------------------------------------------------------------
def test_invalid_pint_string(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Scalar["invalid_unit_xyz"]) -> float: ...

        x: meter
        travel(x)
    """)
    # Invalid units should either error or be treated as Any (no dimension mismatch)
    # We just check it doesn't crash
    assert "Internal error" not in out


# ===========================================================================
# Quantity(val, "unit_str") constructor escape hatch
# ===========================================================================


# ---------------------------------------------------------------------------
# 60. Quantity(val, "m") is accepted as meter
# ---------------------------------------------------------------------------
def test_quantity_unit_str_constructor_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        x: meter = Quantity(1.0, "m")
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 61. Quantity(val, "km") is accepted as kilometer
# ---------------------------------------------------------------------------
def test_quantity_unit_str_constructor_km(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        x: kilometer = Quantity(1.0, "km")
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 62. Quantity(val, "m") assigned to second — dimension mismatch on assignment
# ---------------------------------------------------------------------------
def test_quantity_unit_str_constructor_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        x: second = Quantity(1.0, "m")
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 63. Quantity(val, "unknown_unit") — plugin reports unknown unit
# ---------------------------------------------------------------------------
def test_quantity_unit_str_constructor_unknown(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        x = Quantity(1.0, "unknown_unit_xyz_abc")
    """)
    assert "Unknown unit" in out


# ===========================================================================
# q.to("unit_str") escape hatch
# ===========================================================================


# ---------------------------------------------------------------------------
# 64. q.to("m/s") accepted as meter_per_second
# ---------------------------------------------------------------------------
def test_to_correct_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        q = Quantity(3.6, "km/h")
        x: meter_per_second = q.to("m/s")
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 67. Full chain: constructor / constructor → .to() returns correct dim
# ---------------------------------------------------------------------------
def test_to_chain_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d = Quantity(100.0, "m")
        t = Quantity(10.0, "s")
        v: kilometer_per_hour = (d / t).to("km/h")
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 68. .to() result is tracked: a wrong downstream annotation is caught
# (previously .to() returned Quantity[Any], so this slipped through).
# ---------------------------------------------------------------------------
def test_to_result_tracked_wrong_assignment(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        q = Quantity(3.6, "km/h")
        x: kilogram = q.to("m/s")   # m/s tracked, assigned to kilogram
    """)
    assert "error:" in out, out


# ---------------------------------------------------------------------------
# 69. .to() across incompatible dimensions — pint raises at runtime; flagged.
# ---------------------------------------------------------------------------
def test_to_incompatible_dimension(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        bad = Quantity(5.0, "s").to("m")   # [time] -> [length]
    """)
    assert "Dimension mismatch in conversion" in out, out


# ---------------------------------------------------------------------------
# 70. .to() with an unknown unit string is reported.
# ---------------------------------------------------------------------------
def test_to_unknown_unit(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        q = Quantity(1.0, "m")
        bad = q.to("florgle_xyz")
    """)
    assert "Unknown unit" in out, out


# ---------------------------------------------------------------------------
# 71. .to() escapes from an unknown (Quantity[Any]) receiver into a tracked
# type — no dimension check is possible, but the result is anchored.
# ---------------------------------------------------------------------------
def test_to_escapes_from_any_receiver(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def g(x: Quantity) -> None:
            y: meter_per_second = x.to("m/s")
    """)
    no_error(out)


# ===========================================================================
# Runtime: pint-backed Quantity mechanics
# ===========================================================================


def test_runtime_quantity_unit_str_value() -> None:
    from mypy_units import Quantity

    q = Quantity(1000.0, "m")
    assert float(q) == 1000.0


def test_runtime_to_converts_correctly() -> None:
    from mypy_units import Quantity

    q = Quantity(1000.0, "m")
    result = q.to("km")
    assert abs(float(result) - 1.0) < 1e-9


def test_runtime_to_raises_on_non_pint_backed() -> None:
    import pytest

    from mypy_units import Quantity

    q = Quantity(1.0)
    with pytest.raises(AttributeError):
        q.to("km")  # type: ignore[union-attr]


def test_runtime_arithmetic_preserves_pint_backing() -> None:
    from mypy_units import Quantity

    d = Quantity(3600.0, "m")
    t = Quantity(1.0, "s")
    v = d / t
    result = v.to("km/h")
    assert abs(float(result) - 12960.0) < 1e-6


# ===========================================================================
# Addition / subtraction operand compatibility
#
# Adding or subtracting quantities requires matching dimension AND scale; the
# runtime values are bare floats, so mixing metres and kilometres is a real
# numeric bug, not just a type nicety.
# ===========================================================================


def test_add_wrong_dimension(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> meter:
            return d + t   # [length] + [time]
    """)
    has_mismatch(out)
    assert "Dimension mismatch in addition" in out, out


def test_sub_wrong_dimension(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> meter:
            return d - t   # [length] - [time]
    """)
    has_mismatch(out)
    assert "Dimension mismatch in subtraction" in out, out


def test_add_scale_mismatch(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, k: kilometer) -> meter:
            return d + k   # metre + kilometre: numerically wrong without conversion
    """)
    has_mismatch(out)
    assert "Unit mismatch in addition" in out, out


def test_add_same_dimension_ok(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def total(a: meter, b: meter) -> meter:
            return a + b
    """)
    no_error(out)


def test_sub_same_dimension_ok(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def diff(a: meter, b: meter) -> meter:
            return a - b
    """)
    no_error(out)


def test_add_plain_int_to_quantity_rejected(mypy_fixture: Callable[[str], str]) -> None:
    # Unlike multiplication, adding a bare scalar to a dimensioned quantity is
    # nonsensical.  An int operand keeps the value a Quantity, so the plugin's
    # __add__ hook fires and reports the dimension mismatch explicitly.
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return d + 1
    """)
    has_mismatch(out)
    assert "Dimension mismatch in addition" in out, out


def test_sub_plain_int_from_quantity_rejected(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return d - 1
    """)
    has_mismatch(out)
    assert "Dimension mismatch in subtraction" in out, out


def test_add_plain_float_to_quantity_rejected(mypy_fixture: Callable[[str], str]) -> None:
    # A float operand is a special case: scalar Quantity subclasses float, so
    # mypy resolves Quantity + float through float's own operator and the result
    # collapses to a bare ``float`` (the unit is *erased*, never silently kept).
    # That is still an error wherever a unit is expected — here, the return type.
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return d + 1.0
    """)
    assert "error:" in out, out
    assert "Dimension mismatch" not in out  # caught as a return-value type error


def test_add_scalar_to_dimensionless_ok(mypy_fixture: Callable[[str], str]) -> None:
    # A dimensionless quantity (ratio, radian, …) may be combined with a scalar.
    out = mypy_fixture("""
        from mypy_units.units import dimensionless, radian
        def bump(r: dimensionless) -> dimensionless:
            return r + 1
        def turn(a: radian) -> radian:
            return a - 1
    """)
    no_error(out)


def test_array_add_wrong_dimension(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: Array[meter], t: Array[second]) -> Array[meter]:
            return d + t
    """)
    has_mismatch(out)
    assert "Dimension mismatch in addition" in out, out


def test_array_add_same_dimension_ok(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def total(a: Array[meter], b: Array[meter]) -> Array[meter]:
            return a + b
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# Quantity[Any] operands in arithmetic — a unit carrier whose dimension is
# statically unknown (bare Quantity(x), an unannotated value, an untyped helper
# return).  Such an operand makes the whole expression undecidable and is
# flagged in *every* arithmetic operation, in either order.  Detection is by
# static type, so the variable case is caught too (not only inline calls).
# A unit-tagged Quantity(v, "unit") and plain scalars are unaffected.
# ---------------------------------------------------------------------------


def test_unknown_unit_sub_bare_quantity(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return d - Quantity(1.0)
    """)
    assert "Quantity[Any]" in out, out


def test_unknown_unit_reverse_order(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return Quantity(1.0) - d
    """)
    assert "Quantity[Any]" in out, out


def test_unknown_unit_multiplication(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def f(d: meter, x: Quantity) -> None:
            y = d * x
    """)
    assert "Quantity[Any]" in out and "multiplication" in out, out


def test_unknown_unit_division(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def f(d: meter, x: Quantity) -> None:
            y = d / x
    """)
    assert "Quantity[Any]" in out and "division" in out, out


def test_unknown_unit_power(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def f(x: Quantity) -> None:
            y = x ** 2
    """)
    assert "Quantity[Any]" in out and "exponentiation" in out, out


def test_unknown_unit_variable_case(mypy_fixture: Callable[[str], str]) -> None:
    # Detection is by static type, so a bare Quantity bound to a variable is
    # caught just like an inline call.
    out = mypy_fixture("""
        def f(d: meter) -> None:
            x = Quantity(1.0)
            y = d * x
    """)
    assert "Quantity[Any]" in out, out


def test_tagged_quantity_ok(mypy_fixture: Callable[[str], str]) -> None:
    # A unit-tagged Quantity(value, "unit") is tracked — positional or keyword.
    out = mypy_fixture("""
        def shift(d: meter) -> meter:
            return d + Quantity(1.0, "m")
        def shift_kw(d: meter) -> meter:
            return d + Quantity(1.0, unit="m")
        def scale(d: meter) -> square_meter:
            return d * Quantity(1.0, "m")
    """)
    no_error(out)


def test_plain_scalar_multiplication_ok(mypy_fixture: Callable[[str], str]) -> None:
    # Plain scalars are not Quantity[Any]; multiplicative scaling stays valid.
    out = mypy_fixture("""
        def half(d: meter) -> meter:
            return d * 0.5
    """)
    no_error(out)


# ===========================================================================
# Canonical round-trip guard
#
# Every unit alias in mypy_units.units hard-codes a canonical literal string
# (e.g. meter = Quantity[Literal["1000 meter"]]).  The plugin's arithmetic
# hooks recompute canonicals via _fmt_canonical and mypy compares the result
# Literal *string* structurally against the annotation.  If a hand-written
# alias string differs from what the pipeline produces, an identity function
# (foo -> foo) is wrongly rejected, or the value-based check silently no-ops.
# This test pins every alias to the form the plugin actually produces, so any
# future drift (or a newly added alias) fails loudly here instead of in users'
# code.
# ===========================================================================


def _unit_aliases() -> list[tuple[str, str]]:
    """Return (alias_name, declared_literal_string) for every unit alias."""
    from typing import get_args

    from mypy_units import units

    out: list[tuple[str, str]] = []
    for name in dir(units):
        if name.startswith("_"):
            continue
        alias_args = get_args(getattr(units, name))
        if not alias_args:
            continue
        literal_args = get_args(alias_args[0])  # unwrap Literal["..."]
        if literal_args and isinstance(literal_args[0], str):
            out.append((name, literal_args[0]))
    return out


def _plugin_canonical(literal: str) -> str:
    """What the plugin computes for a value of this unit (see _canonical/_check)."""
    from mypy_units.dimension import _fmt_canonical, parse_base_literal

    base = parse_base_literal(literal).to_base_units()
    return _fmt_canonical(float(base.magnitude), str(base.units))


def test_unit_aliases_discovered() -> None:
    # Guard against the introspection silently finding nothing.
    assert len(_unit_aliases()) > 40


@pytest.mark.parametrize(
    ("name", "literal"), _unit_aliases(), ids=lambda v: v if isinstance(v, str) else ""
)
def test_alias_literal_is_canonical(name: str, literal: str) -> None:
    """The declared alias string must equal the plugin-computed canonical.

    Otherwise mypy's structural Literal comparison rejects identity functions
    (foot -> foot) even though the dimensions match, and parse_base_literal may
    fail to round-trip (the historical hertz "1 / second" bug).
    """
    computed = _plugin_canonical(literal)
    assert computed == literal, (
        f"Alias {name!r} declares Literal[{literal!r}] but the plugin computes "
        f"{computed!r} for that unit. mypy compares these strings structurally, "
        f"so they must match exactly. Update the alias in mypy_units/units.py."
    )
