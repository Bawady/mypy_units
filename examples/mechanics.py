"""Classical mechanics — dimension-checked with mypy_units.

Run:         python examples/mechanics.py
Type-check:  mypy examples/mechanics.py
"""
from __future__ import annotations

import numpy as np

from mypy_units import Quantity
from mypy_units.units import (
    acceleration,
    area,
    energy,
    force,
    joule,
    kilogram,
    length,
    mass,
    meter,
    meter_per_second,
    meter_per_second_squared,
    newton,
    pressure,
    second,
    time,
    velocity,
)
from mypy_units.units import power as mech_power  # avoid clash with np.power

# ---------------------------------------------------------------------------
# Elementary laws (one-liners — show that formula structure encodes the units)
# ---------------------------------------------------------------------------

def newton_second(m: mass, a: acceleration) -> force:
    """F = m·a  →  [mass]·[length/time²] = [mass·length/time²]"""
    return m * a


def work(f: force, d: length) -> energy:
    """W = F·d  →  [mass·length/time²]·[length] = [mass·length²/time²]"""
    return f * d


def mechanical_power(w: energy, t: time) -> mech_power:
    """P = W/t  →  [mass·length²/time²] / [time] = [mass·length²/time³]"""
    return w / t


def gravitational_pe(m: mass, g: acceleration, h: length) -> energy:
    """E_p = m·g·h  →  [mass]·[length/time²]·[length] = [mass·length²/time²]"""
    return m * g * h


def surface_pressure(f: force, a: area) -> pressure:
    """σ = F/A  →  [mass·length/time²] / [length²] = [mass/length/time²]"""
    return f / a


def freefall_speed(g: acceleration, h: length) -> velocity:
    """v = sqrt(g·h)  — dimensional structure of v²=g·h; factor √2 omitted.

    g·h → [length/time²]·[length] = [length²/time²]
    sqrt → [length/time] = velocity ✓
    """
    return np.sqrt(g * h)


def pendulum_period(L: length, g: acceleration) -> time:
    """T = sqrt(L/g)  — factor 2π omitted.

    L/g → [length] / [length/time²] = [time²]
    sqrt → [time] ✓
    """
    return np.sqrt(L / g)


# ---------------------------------------------------------------------------
# Kinematics with branching
# ---------------------------------------------------------------------------

def stopping_distance(v: velocity, a: acceleration, t_react: time) -> length:
    """Total braking distance = reaction gap + kinematic stopping gap.

    Dimension trace:
      v · t_react  → [length/time]·[time]            = [length]
      v² / a       → [length/time]² / [length/time²] = [length]
      sum          → [length] + [length]              = [length] ✓
    """
    reaction_gap: length = v * t_react
    braking_gap: length  = v * v / a
    return reaction_gap + braking_gap


def clamp_velocity(v: velocity, v_max: velocity) -> velocity:
    """Return v if within the speed limit, otherwise v_max."""
    if v > v_max:
        return v_max
    return v


def trajectory_euler(
    x: length,
    v: velocity,
    a: acceleration,
    dt: time,
    x_wall: length,
) -> tuple[length, velocity]:
    """Single Euler integration step with an elastic wall at x_wall.

    Dimension trace:
      a · dt       → [length/time²]·[time]  = [length/time] = velocity
      v + a·dt     → velocity + velocity    = velocity       ✓
      v · dt       → [length/time]·[time]   = [length]       = length
      x + v·dt     → length + length        = length         ✓

    On wall contact: position is clamped to x_wall (still [length]);
    velocity is negated via __neg__, which the plugin tracks — result is
    still [velocity].
    """
    new_v: velocity = v + a * dt
    new_x: length   = x + v * dt

    if new_x >= x_wall:
        new_x = x_wall
        new_v = -new_v      # __neg__ hook: returns same dimension as new_v

    return new_x, new_v


def simulate_bounce(
    x0: length,
    v0: velocity,
    a: acceleration,
    dt: time,
    x_wall: length,
    steps: int,
) -> list[float]:
    """Run the Euler bouncer for *steps* iterations; return position values."""
    x: length   = x0
    v: velocity = v0
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

    v0: meter_per_second            = Quantity(30.0)
    a_brake: meter_per_second_squared = Quantity(7.0)
    t_react: second                 = Quantity(1.5)
    d_stop: meter = stopping_distance(v0, a_brake, t_react)
    print(f"Stopping distance: {d_stop.value:.1f} m")

    T_pend: second = pendulum_period(Quantity(1.0), g_ms2)
    print(f"Pendulum period (L=1 m): {T_pend.value:.3f} s")

    wall: meter = Quantity(10.0)
    traj = simulate_bounce(
        Quantity(0.0), Quantity(5.0), Quantity(0.0), Quantity(0.1), wall, steps=30
    )
    print(f"Bounce positions (first 5): {[f'{p:.1f}' for p in traj[:5]]}")
