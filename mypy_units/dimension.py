from __future__ import annotations

import functools
import re
from fractions import Fraction
from typing import Any

try:
    import pintrs as pint
except ImportError:
    import pint  # type: ignore[no-redef]

_ureg: pint.UnitRegistry | None = None


def _registry() -> pint.UnitRegistry:
    global _ureg
    if _ureg is None:
        _ureg = pint.UnitRegistry()
    return _ureg


# ---------------------------------------------------------------------------
# DimDict — library-agnostic dimension representation
#
# Maps dimension name (e.g. "[length]") to a Fraction exponent.
# Fraction supports rational exponents needed for sqrt/cbrt.
# An empty dict represents a dimensionless quantity.
# ---------------------------------------------------------------------------

DimDict = dict[str, Fraction]


def _fmt_exp(v: Fraction) -> str:
    if v == 1:
        return ""
    if v.denominator == 1:
        return f" ** {v.numerator}"
    return f" ** ({v.numerator}/{v.denominator})"


def canonical_dim_str(d: DimDict) -> str:
    """Format a DimDict as a canonical string.

    Keys are sorted alphabetically; positive exponents come first, negative
    exponents follow after ' / '.  Examples::

        {"[length]": Fraction(1), "[time]": Fraction(-1)}  ->  "[length] / [time]"
        {"[length]": Fraction(1,2)}  ->  "[length] ** (1/2)"
        {}  ->  "dimensionless"
    """
    if not d:
        return "dimensionless"
    pos = sorted((k, v) for k, v in d.items() if v > 0)
    neg = sorted((k, -v) for k, v in d.items() if v < 0)
    parts = [f"{k}{_fmt_exp(v)}" for k, v in pos]
    result = " * ".join(parts)
    for k, v in neg:
        neg_part = f"{k}{_fmt_exp(v)}"
        result = f"1 / {neg_part}" if not result else f"{result} / {neg_part}"
    return result


def parse_dim_str(s: str) -> DimDict | None:
    """Parse a canonical dim string into a DimDict.

    Handles integer exponents (``** 2``) and fractional exponents (``** (1/2)``).
    """
    if s == "dimensionless":
        return {}
    parts: dict[str, Fraction] = {}
    for sign, chunk in enumerate(re.split(r" / ", s)):
        for term in re.split(r" \* ", chunk.strip()):
            term = term.strip()
            if not term:
                continue
            m = re.fullmatch(
                r"(\[[\w]+\]|\d+)(?:\s*\*\*\s*(\d+|\(\d+/\d+\)))?", term
            )
            if m is None:
                return None
            key, exp_str = m.group(1), m.group(2)
            if key == "1":
                continue
            if exp_str is None:
                exp = Fraction(1)
            elif exp_str.startswith("("):
                num, den = exp_str[1:-1].split("/")
                exp = Fraction(int(num), int(den))
            else:
                exp = Fraction(int(exp_str))
            parts[key] = parts.get(key, Fraction(0)) + (exp if sign == 0 else -exp)
    return {k: v for k, v in parts.items() if v != 0}


@functools.lru_cache(maxsize=256)
def _unit_to_dim(unit_str: str) -> DimDict | None:
    """Look up the dimensionality of a unit string via the pint/pintrs registry."""
    try:
        ureg = _registry()
        q = ureg.parse_expression(unit_str)
        items = q.dimensionality.items()  # type: ignore[attr-defined]
        return {k: Fraction(int(v)) for k, v in items if int(v) != 0}
    except Exception:
        return None


@functools.lru_cache(maxsize=256)
def resolve(s: str) -> DimDict | None:
    """Resolve *s* as a canonical dim string, a unit string, or a pint dim string.

    Returns ``None`` when *s* cannot be parsed.
    """
    if "[" in s or s == "dimensionless":
        parsed = parse_dim_str(s)
        if parsed is not None:
            return parsed

    result = _unit_to_dim(s)
    if result is not None:
        return result

    return parse_dim_str(s)


def dims_equal(a: DimDict, b: DimDict) -> bool:
    return a == b


# ---------------------------------------------------------------------------
# Arithmetic on DimDicts
# ---------------------------------------------------------------------------

def dim_mul(a: DimDict, b: DimDict) -> DimDict:
    result = dict(a)
    for k, v in b.items():
        result[k] = result.get(k, Fraction(0)) + v
    return {k: v for k, v in result.items() if v != 0}


def dim_div(a: DimDict, b: DimDict) -> DimDict:
    return dim_mul(a, {k: -v for k, v in b.items()})


def dim_pow(a: DimDict, exp: int | float) -> DimDict:
    """Raise dimension to a power; *exp* may be fractional (e.g. 0.5 for sqrt)."""
    frac_exp = Fraction(exp).limit_denominator(1000)
    if frac_exp == 0:
        return {}
    return {k: v * frac_exp for k, v in a.items()}


# ---------------------------------------------------------------------------
# Pint-based canonical literal helpers
#
# The canonical literal is a pint-parseable string that encodes both the
# physical dimension AND the SI base-unit scale factor of a unit.  Examples:
#
#   "m"                          meter (magnitude 1, already base)
#   "1000 m"                     kilometer
#   "3600 s"                     hour
#   "0.277777777777778 m / s"    kilometer_per_hour
#   "dimensionless"              radian / steradian
#   "0.0174532925199433 dimensionless"   degree
#
# Units whose alias names are not directly pint-parseable (e.g. compound
# names like "square_meter") are translated via _UNIT_MAP before the pint
# call.  There is no fallback to dimension-only checking; an unrecognised
# unit string raises ValueError.
# ---------------------------------------------------------------------------

_UNIT_MAP: dict[str, str] = {
    "square_meter":             "m**2",
    "cubic_meter":              "m**3",
    "meter_per_second":         "m/s",
    "kilometer_per_hour":       "km/h",
    "meter_per_second_squared": "m/s**2",
    # Offset temperature units: map to Kelvin-scale equivalents so that
    # only the multiplicative scale factor is used (no offset arithmetic).
    "degC": "K",
    "degF": "0.5555555555555556 K",
}


def _fmt_canonical(magnitude: float, units_str: str) -> str:
    """Format a (magnitude, units) pair into a canonical literal string."""
    if not units_str:
        units_str = "dimensionless"
    if magnitude == 1.0:
        return units_str
    return f"{magnitude:.15g} {units_str}"


@functools.lru_cache(maxsize=512)
def to_base_literal(unit_str: str) -> str:
    """Convert a unit alias string to its pint SI base-unit canonical form.

    The result is a pint-parseable string that encodes both the dimension and
    the scale factor.  Raises ``pint.UndefinedUnitError`` (or similar) for
    unrecognised units — there is no silent fallback.
    """
    pint_str = _UNIT_MAP.get(unit_str, unit_str)
    q = _registry().parse_expression(pint_str).to_base_units()
    return _fmt_canonical(float(q.magnitude), str(q.units))


@functools.lru_cache(maxsize=512)
def parse_base_literal(canonical: str) -> Any:
    """Parse a canonical base-unit literal string back to a pint Quantity."""
    return _registry().parse_expression(canonical).to_base_units()
