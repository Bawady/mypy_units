"""Ideal-gas laws — dimension-checked with mypy_units.

All classical gas laws are expressed as pure dimension-annotated functions.
The mypy plugin verifies every multiplication and division so that a formula
producing the wrong physical dimension is caught at static analysis time.

Run:         python examples/gas_laws.py
Type-check:  mypy examples/gas_laws.py
"""
from __future__ import annotations

from mypy_units import Quantity
from mypy_units.units import (
    cubic_meter,
    kelvin,
    pascal,
    pressure,
    temperature,
    volume,
)

# ---------------------------------------------------------------------------
# Classical gas laws (one-liners)
# ---------------------------------------------------------------------------

def boyles_law(P1: pressure, V1: volume, V2: volume) -> pressure:
    """P2 = P1·V1 / V2  (constant temperature).

    [mass/length/time²]·[length³] / [length³] = [mass/length/time²] ✓
    """
    return P1 * V1 / V2


def charles_law(V1: volume, T1: temperature, T2: temperature) -> volume:
    """V2 = V1·T2 / T1  (constant pressure).

    [length³]·[temperature] / [temperature] = [length³] ✓
    """
    return V1 * T2 / T1


def gay_lussac_law(P1: pressure, T1: temperature, T2: temperature) -> pressure:
    """P2 = P1·T2 / T1  (constant volume).

    [mass/length/time²]·[temperature] / [temperature] = [mass/length/time²] ✓
    """
    return P1 * T2 / T1


def combined_gas_law(
    P1: pressure, V1: volume, T1: temperature,
    V2: volume,  T2: temperature,
) -> pressure:
    """P2 = P1·V1·T2 / (V2·T1).

    Numerator:
      P1·V1  → [mass/length/time²]·[length³] = [mass·length²/time²]  (energy)
      ·T2    → [mass·length²/time²·temperature]
    Denominator:
      V2·T1  → [length³·temperature]
    Ratio:
      [mass·length²·temperature/time²] / [length³·temperature]
      = [mass/length/time²] = pressure ✓
    """
    return P1 * V1 * T2 / (V2 * T1)


# ---------------------------------------------------------------------------
# Moderate arithmetic: clamp + relief valve
# ---------------------------------------------------------------------------

def clamp_pressure(P: pressure, P_min: pressure, P_max: pressure) -> pressure:
    """Clamp P to the interval [P_min, P_max].

    All three parameters and the return value are [pressure]; mypy verifies
    that the three branches are dimensionally consistent.
    """
    if P < P_min:
        return P_min
    if P > P_max:
        return P_max
    return P


def equilibrate(
    P1: pressure, V1: volume, T1: temperature,
    V2: volume,   T2: temperature,
    P_relief: pressure,
) -> pressure:
    """Combined gas law capped by a pressure-relief threshold.

    Two code paths — normal operating pressure and over-pressure —
    both return [pressure].
    """
    P2: pressure = combined_gas_law(P1, V1, T1, V2, T2)
    return clamp_pressure(P2, Quantity(0), P_relief)


# ---------------------------------------------------------------------------
# Elaborate: law selection with branching + multi-step dimension arithmetic
# ---------------------------------------------------------------------------

def select_law(
    P1: pressure, V1: volume, T1: temperature,
    new_V: volume,   V_changed: bool,
    new_T: temperature, T_changed: bool,
) -> pressure:
    """Dispatch to the appropriate gas law based on what changed.

    Four branches, each returning [pressure]:
      both changed  → combined gas law   (P1·V1·T2 / V2·T1)
      T only        → Gay-Lussac         (P1·T2 / T1)
      V only        → Boyle's            (P1·V1 / V2)
      neither       → pressure unchanged
    """
    if T_changed and V_changed:
        return combined_gas_law(P1, V1, T1, new_V, new_T)
    if T_changed:
        return gay_lussac_law(P1, T1, new_T)
    if V_changed:
        return boyles_law(P1, V1, new_V)
    return P1


def compression_ratio(
    P1: pressure, V1: volume, T1: temperature,
    V2: volume,   T2: temperature,
    P_atm: pressure,
) -> pressure:
    """Compute final gauge pressure = P2 − P_atm after a compression cycle.

    Gauge pressure is the excess above ambient — still [pressure].

    Dimension trace:
      P2      = combined_gas_law(...)         → [pressure]
      P2-P_atm → [pressure] − [pressure]     = [pressure] ✓

    Additionally clamp to zero so that negative gauge values are suppressed.
    """
    P2: pressure = combined_gas_law(P1, V1, T1, V2, T2)
    gauge = P2 - P_atm
    zero: pressure  = Quantity(0)
    if gauge < zero:
        return zero
    return gauge


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    P0: pascal      = Quantity(101_325.0)   # 1 atm
    V0: cubic_meter = Quantity(1.0)
    T0: kelvin      = Quantity(300.0)       # ~27 °C

    V_half: cubic_meter = Quantity(0.5)
    T_hot: kelvin       = Quantity(600.0)
    T_cold: kelvin      = Quantity(150.0)

    P_boyle: pascal = boyles_law(P0, V0, V_half)
    print(f"Boyle (V→V/2):        P = {P_boyle.value:.0f} Pa  ({P_boyle.value/1e5:.2f} bar)")

    V_charles: cubic_meter = charles_law(V0, T0, T_hot)
    print(f"Charles (T→2T):       V = {V_charles.value:.2f} m³")

    P_gl: pascal = gay_lussac_law(P0, T0, T_cold)
    print(f"Gay-Lussac (T→T/2):   P = {P_gl.value:.0f} Pa  ({P_gl.value/1e5:.2f} bar)")

    P_comb: pascal = combined_gas_law(P0, V0, T0, V_half, T_hot)
    print(f"Combined (V/2, 2T):   P = {P_comb.value:.0f} Pa  ({P_comb.value/1e5:.2f} bar)")

    P_relief: pascal = Quantity(300_000.0)  # 3 bar relief valve
    P_eq: pascal = equilibrate(P0, V0, T0, V_half, T_hot, P_relief)
    print(f"Equilibrate (3 bar cap):  P = {P_eq.value:.0f} Pa")

    P_auto: pascal = select_law(P0, V0, T0,
                                new_V=V_half, V_changed=True,
                                new_T=T_hot,  T_changed=True)
    print(f"select_law (both changed): P = {P_auto.value:.0f} Pa")

    gauge: pascal = compression_ratio(P0, V0, T0, V_half, T_hot, P0)
    print(f"Gauge pressure after compression: {gauge.value:.0f} Pa  ({gauge.value/1e5:.2f} bar)")
