"""Classical mechanics — dimension-checked with mypy_units.

Run:         python examples/mechanics.py
Type-check:  mypy examples/mechanics.py
"""
from __future__ import annotations

import numpy as np

from mypy_units import Quantity
from mypy_units.units import (
    joule,
    kilogram,
    meter,
    meter_per_second,
    meter_per_second_squared,
    newton,
    pascal,
    second,
    square_meter,
)
from mypy_units.units import watt as mech_watt  # avoid clash with np.power

# ---------------------------------------------------------------------------
# Elementary laws (one-liners — show that formula structure encodes the units)
# ---------------------------------------------------------------------------

def newton_second(m: kilogram, a: meter_per_second_squared) -> newton:
    """F = m·a"""
    return m * a


def work(f: newton, d: meter) -> joule:
    """W = F·d"""
    return f * d


def mechanical_power(w: joule, t: second) -> mech_watt:
    """P = W/t"""
    return w / t


def gravitational_pe(m: kilogram, g: meter_per_second_squared, h: meter) -> joule:
    """E_p = m·g·h"""
    return m * g * h


def surface_pressure(f: newton, a: square_meter) -> pascal:
    """σ = F/A"""
    return f / a


def freefall_speed(g: meter_per_second_squared, h: meter) -> meter_per_second:
    """v = sqrt(g·h)  — dimensional structure of v²=g·h; factor √2 omitted.

    g·h → meter_per_second_squared · meter = meter²/second²
    sqrt → meter/second ✓
    """
    return np.sqrt(g * h)


def pendulum_period(L: meter, g: meter_per_second_squared) -> second:
    """T = sqrt(L/g)  — factor 2π omitted.

    L/g → meter / (meter/second²) = second²
    sqrt → second ✓
    """
    return np.sqrt(L / g)


# ---------------------------------------------------------------------------
# Kinematics with branching
# ---------------------------------------------------------------------------

def stopping_distance(
    v: meter_per_second, a: meter_per_second_squared, t_react: second
) -> meter:
    """Total braking distance = reaction gap + kinematic stopping gap.

    Dimension trace:
      v · t_react  → meter/second · second              = meter
      v² / a       → (meter/second)² / (meter/second²)  = meter
      sum          → meter + meter                       = meter ✓
    """
    reaction_gap: meter = v * t_react
    braking_gap: meter  = v * v / a
    return reaction_gap + braking_gap


def clamp_velocity(v: meter_per_second, v_max: meter_per_second) -> meter_per_second:
    """Return v if within the speed limit, otherwise v_max."""
    if v > v_max:
        return v_max
    return v


def trajectory_euler(
    x: meter,
    v: meter_per_second,
    a: meter_per_second_squared,
    dt: second,
    x_wall: meter,
) -> tuple[meter, meter_per_second]:
    """Single Euler integration step with an elastic wall at x_wall.

    Dimension trace:
      a · dt       → meter/second² · second = meter/second
      v + a·dt     → meter/second + meter/second = meter/second  ✓
      v · dt       → meter/second · second   = meter
      x + v·dt     → meter + meter           = meter             ✓

    On wall contact: velocity is negated via __neg__, which the plugin
    tracks — result is still meter_per_second.
    """
    new_v: meter_per_second = v + a * dt
    new_x: meter            = x + v * dt

    if new_x >= x_wall:
        new_x = x_wall
        new_v = -new_v

    return new_x, new_v


def simulate_bounce(
    x0: meter,
    v0: meter_per_second,
    a: meter_per_second_squared,
    dt: second,
    x_wall: meter,
    steps: int,
) -> list[float]:
    """Run the Euler bouncer for *steps* iterations; return position values."""
    x: meter             = x0
    v: meter_per_second  = v0
    positions: list[float] = []
    for _ in range(steps):
        x, v = trajectory_euler(x, v, a, dt, x_wall)
        positions.append(x.value)
    return positions


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    m_kg: kilogram                  = Quantity(70.0)
    g_ms2: meter_per_second_squared = Quantity(9.81)
    h_m: meter                      = Quantity(50.0)

    W: newton  = newton_second(m_kg, g_ms2)
    Ep: joule  = gravitational_pe(m_kg, g_ms2, h_m)
    v_imp: meter_per_second = freefall_speed(g_ms2, h_m)

    print(f"Weight:           {W.value:.1f} N")
    print(f"Potential energy: {Ep.value:.0f} J")
    print(f"Impact speed:     {v_imp.value:.2f} m/s")

    v0: meter_per_second              = Quantity(30.0)
    a_brake: meter_per_second_squared = Quantity(7.0)
    t_react: second                   = Quantity(1.5)
    d_stop: meter = stopping_distance(v0, a_brake, t_react)
    print(f"Stopping distance: {d_stop.value:.1f} m")

    T_pend: second = pendulum_period(Quantity(1.0), g_ms2)
    print(f"Pendulum period (L=1 m): {T_pend.value:.3f} s")

    wall: meter = Quantity(10.0)
    traj = simulate_bounce(
        Quantity(0.0), Quantity(5.0), Quantity(0.0), Quantity(0.1), wall, steps=30
    )
    print(f"Bounce positions (first 5): {[f'{p:.1f}' for p in traj[:5]]}")
