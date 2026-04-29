"""Wave physics — dimension-checked with mypy_units.

Run:         python examples/waves.py
Type-check:  mypy examples/waves.py
"""
from __future__ import annotations

from mypy_units import Quantity
from mypy_units.units import (
    frequency,
    hertz,
    length,
    meter,
    meter_per_second,
    second,
    time,
    velocity,
)

# ---------------------------------------------------------------------------
# Elementary wave relations
# ---------------------------------------------------------------------------

def wavelength(c: velocity, f: frequency) -> length:
    """λ = c / f

    [length/time] / [1/time] = [length/time]·[time] = [length] ✓
    """
    return c / f


def period(f: frequency) -> time:
    """T = 1 / f

    1 / [1/time] = [time] ✓  (tracked via __rtruediv__ hook)
    """
    return 1 / f


def wave_speed(lam: length, f: frequency) -> velocity:
    """c = λ · f

    [length]·[1/time] = [length/time] ✓
    """
    return lam * f


def beat_frequency(f1: frequency, f2: frequency) -> frequency:
    """|f1 - f2|; both arguments and the result are [1/time].

    Negative difference is negated via __neg__ — the plugin returns the
    same dimension, so the result is still [frequency].
    """
    diff: frequency = f1 - f2
    if diff < Quantity(0):
        return -diff
    return diff


def doppler_observed(
    f0: frequency,
    c: velocity,
    v_source: velocity,
) -> frequency:
    """Classic Doppler shift for a receding source: f' = f0 · c / (c + v_source).

    Dimension trace:
      c + v_source   → velocity + velocity     = velocity      (same dim)
      c / (c+v_s)    → velocity / velocity     = dimensionless ✓
      f0 * ratio     → [1/time] · dimensionless = [1/time]     ✓
    """
    relative: velocity = c + v_source
    ratio = c / relative
    return f0 * ratio


# ---------------------------------------------------------------------------
# Resonant cavity — moderate arithmetic plus a branch
# ---------------------------------------------------------------------------

def resonant_length(
    c: velocity,
    f: frequency,
    n: int,
    closed_end: bool,
) -> length:
    """Pipe length for the n-th harmonic.

    Open pipe (or open string):  L = n · λ / 2
    One-end-closed pipe:         L = (2n−1) · λ / 4

    Multiplying [length] by a plain int preserves the [length] dimension
    (the plugin treats plain int/float operands as dimensionless).
    Likewise for integer division.
    """
    lam: length = wavelength(c, f)
    if closed_end:
        return lam * (2 * n - 1) / 4
    return lam * n / 2


# ---------------------------------------------------------------------------
# Standing-wave spectrum — branching over multiple harmonics
# ---------------------------------------------------------------------------

def harmonic_frequencies(
    c: velocity,
    L: length,
    n_max: int,
    closed_end: bool,
) -> list[float]:
    """Return the first n_max resonant frequencies (Hz values) for a pipe.

    Open:   f_n = n · c / (2L)      n = 1, 2, 3, …
    Closed: f_n = (2n−1) · c / (4L)  n = 1, 2, 3, …

    Dimension trace for open case:
      c / (2 · L) → [length/time] / [length] = [1/time] = frequency
      n · (...)   → dimensionless · [1/time]  = [1/time] ✓
    """
    base: frequency = c / L     # [length/time] / [length] = [1/time] ✓
    result: list[float] = []
    for n in range(1, n_max + 1):
        if closed_end:
            f: frequency = base * (2 * n - 1) / 4
        else:
            f = base * n / 2
        result.append(f.value)
    return result


# ---------------------------------------------------------------------------
# Classify by frequency range — pure branching on quantity comparisons
# ---------------------------------------------------------------------------

def audio_band(
    f: frequency,
    f_low: frequency,
    f_high: frequency,
) -> str:
    """Return 'infrasound', 'audible', or 'ultrasound'."""
    if f < f_low:
        return "infrasound"
    if f > f_high:
        return "ultrasound"
    return "audible"


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    c_air: meter_per_second = Quantity(343.0)   # speed of sound in air

    f_a4: hertz = Quantity(440.0)               # A4 concert pitch
    lam_a4: meter  = wavelength(c_air, f_a4)
    T_a4: second   = period(f_a4)

    print(f"A4 (440 Hz) wavelength: {lam_a4.value:.4f} m")
    print(f"A4 period:              {T_a4.value * 1000:.4f} ms")

    f_low: hertz  = Quantity(20.0)
    f_high: hertz = Quantity(20_000.0)
    for f_val in [5.0, 1000.0, 50_000.0]:
        f: hertz = Quantity(f_val)
        band = audio_band(f, f_low, f_high)
        print(f"  {f_val:8.0f} Hz  →  {band}")

    L_pipe: meter = Quantity(0.5)
    print("\nHarmonics for 0.5 m open pipe (Hz):",
          harmonic_frequencies(c_air, L_pipe, n_max=5, closed_end=False))
    print("Harmonics for 0.5 m closed pipe (Hz):",
          harmonic_frequencies(c_air, L_pipe, n_max=5, closed_end=True))

    L_open: meter   = resonant_length(c_air, f_a4, n=1, closed_end=False)
    L_closed: meter = resonant_length(c_air, f_a4, n=1, closed_end=True)
    print(f"\nOpen pipe  (1st harmonic, A4): {L_open.value:.4f} m")
    print(f"Closed pipe (1st harmonic, A4): {L_closed.value:.4f} m")

    f_beat: hertz = beat_frequency(Quantity(440.0), Quantity(441.5))
    print(f"\nBeat frequency (440 vs 441.5 Hz): {f_beat.value} Hz")

    v_src: meter_per_second = Quantity(34.3)    # source at 10% of sound speed
    f_obs: hertz = doppler_observed(f_a4, c_air, v_src)
    print(f"Doppler (source receding at 34.3 m/s): {f_obs.value:.1f} Hz")
