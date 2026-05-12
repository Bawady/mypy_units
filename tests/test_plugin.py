"""Tests for mypy_units plugin — invokes real mypy on inline fixtures."""
from __future__ import annotations

from collections.abc import Callable


def no_error(output: str) -> None:
    assert "Dimension mismatch" not in output, f"Unexpected error:\n{output}"
    unexpected = [
        line for line in output.splitlines()
        if "error:" in line and "[empty-body]" not in line
    ]
    assert not unexpected, "Unexpected mypy error:\n" + "\n".join(unexpected)


def has_mismatch(output: str, arg: str | None = None) -> None:
    assert "Dimension mismatch" in output, f"Expected dimension mismatch, got:\n{output}"
    if arg:
        assert arg in output, f"Expected mismatch on '{arg}', got:\n{output}"


# ---------------------------------------------------------------------------
# 1. Unit→Unit same dimension (kilometer passed where meter expected)
# ---------------------------------------------------------------------------
def test_unit_to_unit_same_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: meter) -> float: ...

        x: kilometer
        travel(x)
    """)
    no_error(out)


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
# 4. Multiple unit aliases of the same dimension are all interchangeable
# ---------------------------------------------------------------------------
def test_same_dim_units_interchangeable(mypy_fixture: Callable[[str], str]) -> None:
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
    no_error(out)


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
# 7. Multi-parameter function — error only on wrong argument
# ---------------------------------------------------------------------------
def test_multi_param_partial_error(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(distance: meter, time: second) -> float: ...

        d: kilometer    # [length] ✓
        t: kilogram     # [mass]   ✗

        speed(d, t)
    """)
    has_mismatch(out, "time")
    assert "distance" not in out, f"False positive on 'distance':\n{out}"


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
# 9. Dimensionless: radian and degree are interchangeable
# ---------------------------------------------------------------------------
def test_dimensionless(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        from mypy_units.units import degree

        def rotate(angle: radian) -> float: ...

        d: degree
        rotate(d)
    """)
    no_error(out)


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

        d_arr: Array[kilometer] = Array(np.array([1.0, 2.0, 3.0]))
        travel(d_arr)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 15. Array[unit] wrong dimension — caught
# ---------------------------------------------------------------------------
def test_numpy_array_wrong_dim(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel(d: Array[kilometer]) -> float: ...

        t_arr: Array[second] = Array(np.array([1.0, 2.0]))
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

        d_arr: Array[meter] = Array(np.array([1.0, 2.0]))
        func(d_arr)
    """)
    assert "error:" in out, f"Expected type error:\n{out}"
    assert "Dimension mismatch" not in out, f"Expected type error, not dim mismatch:\n{out}"


# ---------------------------------------------------------------------------
# 31. Array with same-dimension alias — interchangeable (like scalars)
# ---------------------------------------------------------------------------
def test_array_same_dim_interchangeable(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(d: Array[meter]) -> float: ...

        d_km: Array[kilometer] = Array(np.array([1.0, 2.0]))
        func(d_km)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 32. Function with Array and scalar params — correct call, no error
# ---------------------------------------------------------------------------
def test_mixed_params_call_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def func(arr: Array[meter_per_second], t: second) -> Array[meter]:
            return arr * t

        v_arr: Array[meter_per_second] = Array(np.array([1.0, 2.0]))
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

        v_arr: Array[meter_per_second] = Array(np.array([1.0, 2.0]))
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

        v_arr: Array[meter] = Array(np.array([1.0, 2.0]))   # wrong dim
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

    from mypy_units import Array
    with pytest.raises(TypeError, match="numeric"):
        Array(np.array(["hello", "world"]))


def test_array_accepts_float64_dtype() -> None:
    import numpy as np

    from mypy_units import Array
    arr = Array(np.array([1.0, 2.0, 3.0]))
    assert arr.value.dtype == np.float64


def test_array_accepts_integer_dtype() -> None:
    import numpy as np

    from mypy_units import Array
    arr = Array(np.array([1, 2, 3]))
    assert np.issubdtype(arr.value.dtype, np.integer)


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
# 35. ConversionFactor: 3.6 * (m/s) → km/h — accepted
# ---------------------------------------------------------------------------
def test_conversion_factor_mul_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_in_kmh(d: meter, t: second) -> kilometer_per_hour:
            return ConversionFactor(3.6) * d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 36. ConversionFactor: wrong factor — return-value error
# ---------------------------------------------------------------------------
def test_conversion_factor_wrong_value(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def bad(d: meter, t: second) -> kilometer_per_hour:
            return ConversionFactor(1) * d / t   # 1 m/s ≠ km/h scale
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 37. ConversionFactor: (second) / ConversionFactor(3600) → hour — accepted
# ---------------------------------------------------------------------------
def test_conversion_factor_div_correct(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def travel_time_hours(d: meter, v: meter_per_second) -> hour:
            return (d / v) / ConversionFactor(3600)
    """)
    no_error(out)


# ===========================================================================
# ConversionFactor: comprehensive positive / negative test suite
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
            return ConversionFactor(2) * d / t   # 2 ≠ 3.6
    """)
    assert "error:" in out
    assert "return-value" in out or "Incompatible return value" in out


# ---------------------------------------------------------------------------
# 41. CF(1) on already-correct expression — type is preserved, no error
# ---------------------------------------------------------------------------
def test_cf_unity_preserves_correct_type(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed(d: meter, t: second) -> meter_per_second:
            return ConversionFactor(1) * d / t   # CF(1): scale / 1 = unchanged
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 42. CF(1) does NOT fix a scale-wrong expression — still fails
# ---------------------------------------------------------------------------
def test_cf_unity_does_not_fix_wrong_scale(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        def speed_wrong(d: meter, t: second) -> kilometer_per_hour:
            return ConversionFactor(1) * d / t   # m/s ≠ km/h regardless of CF(1)
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
        v: kilometer_per_hour = ConversionFactor(3.6) * d / t
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 44. CF in a variable assignment — wrong factor rejected
# ---------------------------------------------------------------------------
def test_cf_assignment_wrong_factor(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d: meter = Quantity(100.0)
        t: second = Quantity(50.0)
        v: kilometer_per_hour = ConversionFactor(2) * d / t   # 2 ≠ 3.6
    """)
    assert "error:" in out


# ---------------------------------------------------------------------------
# 45. Assign meter Quantity to kilometer via division by ConversionFactor(1000)
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_div(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_m: meter = Quantity(1000.0)
        d_km: kilometer = d_m / ConversionFactor(1000)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 46. Assign kilometer Quantity to meter via multiplication by ConversionFactor(1000)
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_mul(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_km: kilometer = Quantity(1.0)
        d_m: meter = d_km * ConversionFactor(1000)
    """)
    no_error(out)


# ---------------------------------------------------------------------------
# 47. Same-dimension unit reassignment with wrong CF value — rejected
# ---------------------------------------------------------------------------
def test_cf_unit_reassign_wrong_factor(mypy_fixture: Callable[[str], str]) -> None:
    out = mypy_fixture("""
        d_m: meter = Quantity(1000.0)
        d_km: kilometer = d_m / ConversionFactor(100)   # 100 ≠ 1000
    """)
    assert "error:" in out
