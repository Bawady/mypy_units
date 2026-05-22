"""Wave physics — dimension-checked with mypy_units.

Run:         python examples/waves.py
Type-check:  mypy examples/waves.py
"""

from __future__ import annotations

from mypy_units import Quantity
from mypy_units.units import (
    hertz,
    meter,
    meter_per_second,
    second,
)

# ---------------------------------------------------------------------------
# Elementary wave relations
# ---------------------------------------------------------------------------


def wavelength(c: meter_per_second, f: hertz) -> meter:
    """λ = c / f

    meter/second / (1/second) = meter ✓
    """
    return c / f


def period(f: hertz) -> second:
    """T = 1 / f

    1 / (1/second) = second ✓  (tracked via __rtruediv__ hook)
    """
    return 1 / f


def wave_speed(lam: meter, f: hertz) -> meter_per_second:
    """c = λ · f

    meter · (1/second) = meter/second ✓
    """
    return lam * f


def beat_frequency(f1: hertz, f2: hertz) -> hertz:
    """|f1 - f2|; both arguments and the result are hertz."""
    diff: hertz = f1 - f2
    if diff < Quantity(0):
        return -diff
    return diff


def doppler_observed(
    f0: hertz,
    c: meter_per_second,
    v_source: meter_per_second,
) -> hertz:
    """Classic Doppler shift for a receding source: f' = f0 · c / (c + v_source).

    Dimension trace:
      c + v_source   → meter/second + meter/second  = meter/second
      c / (c+v_s)    → meter/second / meter/second  = dimensionless
      f0 * ratio     → hertz · dimensionless         = hertz ✓
    """
    relative: meter_per_second = c + v_source
    ratio = c / relative
    return f0 * ratio


# ---------------------------------------------------------------------------
# Resonant cavity — moderate arithmetic plus a branch
# ---------------------------------------------------------------------------


def resonant_length(
    c: meter_per_second,
    f: hertz,
    n: int,
    closed_end: bool,
) -> meter:
    """Pipe length for the n-th harmonic.

    Open pipe (or open string):  L = n · λ / 2
    One-end-closed pipe:         L = (2n−1) · λ / 4
    """
    lam: meter = wavelength(c, f)
    if closed_end:
        return lam * (2 * n - 1) / 4
    return lam * n / 2


# ---------------------------------------------------------------------------
# Standing-wave spectrum — branching over multiple harmonics
# ---------------------------------------------------------------------------


def harmonic_frequencies(
    c: meter_per_second,
    L: meter,
    n_max: int,
    closed_end: bool,
) -> list[float]:
    """Return the first n_max resonant frequencies (Hz values) for a pipe.

    Open:   f_n = n · c / (2L)       n = 1, 2, 3, …
    Closed: f_n = (2n−1) · c / (4L)  n = 1, 2, 3, …

    Dimension trace for open case:
      c / (2 · L) → meter/second / meter = 1/second = hertz
      n · (...)   → dimensionless · hertz = hertz ✓
    """
    base: hertz = c / L
    result: list[float] = []
    for n in range(1, n_max + 1):
        if closed_end:
            f: hertz = base * (2 * n - 1) / 4
        else:
            f = base * n / 2
        result.append(f.value)
    return result


# ---------------------------------------------------------------------------
# Classify by frequency range — pure branching on quantity comparisons
# ---------------------------------------------------------------------------


def audio_band(
    f: hertz,
    f_low: hertz,
    f_high: hertz,
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
    c_air: meter_per_second = Quantity(343.0)  # speed of sound in air

    f_a4: hertz = Quantity(440.0)  # A4 concert pitch
    lam_a4: meter = wavelength(c_air, f_a4)
    T_a4: second = period(f_a4)

    print(f"A4 (440 Hz) wavelength: {lam_a4.value:.4f} m")
    print(f"A4 period:              {T_a4.value * 1000:.4f} ms")

    f_low: hertz = Quantity(20.0)
    f_high: hertz = Quantity(20_000.0)
    for f_val in [5.0, 1000.0, 50_000.0]:
        f: hertz = Quantity(f_val)
        band = audio_band(f, f_low, f_high)
        print(f"  {f_val:8.0f} Hz  →  {band}")

    L_pipe: meter = Quantity(0.5)
    print(
        "\nHarmonics for 0.5 m open pipe (Hz):",
        harmonic_frequencies(c_air, L_pipe, n_max=5, closed_end=False),
    )
    print(
        "Harmonics for 0.5 m closed pipe (Hz):",
        harmonic_frequencies(c_air, L_pipe, n_max=5, closed_end=True),
    )

    L_open: meter = resonant_length(c_air, f_a4, n=1, closed_end=False)
    L_closed: meter = resonant_length(c_air, f_a4, n=1, closed_end=True)
    print(f"\nOpen pipe  (1st harmonic, A4): {L_open.value:.4f} m")
    print(f"Closed pipe (1st harmonic, A4): {L_closed.value:.4f} m")

    f_beat: hertz = beat_frequency(Quantity(440.0), Quantity(441.5))
    print(f"\nBeat frequency (440 vs 441.5 Hz): {f_beat.value} Hz")

    v_src: meter_per_second = Quantity(34.3)  # source at 10% of sound speed
    f_obs: hertz = doppler_observed(f_a4, c_air, v_src)
    print(f"Doppler (source receding at 34.3 m/s): {f_obs.value:.1f} Hz")
