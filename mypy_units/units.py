"""Pre-defined unit type aliases.

Import individual names and use them directly as type annotations::

    from mypy_units.units import meter, second, meter_per_second

    def speed(d: meter, t: second) -> meter_per_second: ...

Each alias encodes both the physical dimension AND the SI base-unit scale
factor as a pint-parseable canonical literal.  The mypy plugin uses this
information to detect both dimension mismatches *and* scaling mismatches in
function bodies and at call sites.
"""
from __future__ import annotations

from typing import Literal

from mypy_units.quantity import Quantity

# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------
meter = Quantity[Literal["meter"]]
kilometer = Quantity[Literal["1000 meter"]]
centimeter = Quantity[Literal["0.01 meter"]]
millimeter = Quantity[Literal["0.001 meter"]]
micrometer = Quantity[Literal["1e-06 meter"]]
nanometer = Quantity[Literal["1e-09 meter"]]
mile = Quantity[Literal["1609.344 meter"]]
yard = Quantity[Literal["0.9144 meter"]]
foot = Quantity[Literal["0.3048 meter"]]
inch = Quantity[Literal["0.0254 meter"]]
nautical_mile = Quantity[Literal["1852 meter"]]
angstrom = Quantity[Literal["1e-10 meter"]]
light_year = Quantity[Literal["9.4607304725808e+15 meter"]]

# ---------------------------------------------------------------------------
# Area / volume
# ---------------------------------------------------------------------------
square_meter = Quantity[Literal["meter ** 2"]]
cubic_meter = Quantity[Literal["meter ** 3"]]
hectare = Quantity[Literal["10000 meter ** 2"]]
liter = Quantity[Literal["0.001 meter ** 3"]]
milliliter = Quantity[Literal["1e-06 meter ** 3"]]

# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------
second = Quantity[Literal["second"]]
millisecond = Quantity[Literal["0.001 second"]]
microsecond = Quantity[Literal["1e-06 second"]]
nanosecond = Quantity[Literal["1e-09 second"]]
minute = Quantity[Literal["60 second"]]
hour = Quantity[Literal["3600 second"]]
day = Quantity[Literal["86400 second"]]
week = Quantity[Literal["604800 second"]]
year = Quantity[Literal["31557600 second"]]

# ---------------------------------------------------------------------------
# Mass
# ---------------------------------------------------------------------------
kilogram = Quantity[Literal["kilogram"]]
gram = Quantity[Literal["0.001 kilogram"]]
milligram = Quantity[Literal["1e-06 kilogram"]]
microgram = Quantity[Literal["1e-09 kilogram"]]
tonne = Quantity[Literal["1000 kilogram"]]
pound = Quantity[Literal["0.45359237 kilogram"]]
ounce = Quantity[Literal["0.028349523125 kilogram"]]

# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------
# Note: Temperature units are defined in their native scales.
# Conversions between them require both offset (Offset) and scale (ScaleFactor)
# transformations. The type system tracks the scale, so:
# - degC has scale 1 (relative to itself, same as Kelvin for differences)
# - degF has scale 5/9 (since 1°F = 5/9°C in magnitude)
# - kelvin has scale 1 (absolute temperature)
# To convert °F → °C: subtract 32 (offset), then multiply by 5/9 (scale match)
# To convert °C → °F: multiply by 9/5 (scale), then add 32 (offset)
kelvin = Quantity[Literal["kelvin"]]
degC = Quantity[Literal["kelvin"]]  # Same scale as Kelvin for differences
degF = Quantity[Literal["0.555555555555556 kelvin"]]  # 1°F magnitude = 5/9 K magnitude

# ---------------------------------------------------------------------------
# Electric
# ---------------------------------------------------------------------------
ampere = Quantity[Literal["ampere"]]
milliampere = Quantity[Literal["0.001 ampere"]]
volt = Quantity[Literal["kilogram * meter ** 2 / ampere / second ** 3"]]
millivolt = Quantity[Literal["0.001 kilogram * meter ** 2 / ampere / second ** 3"]]
kilovolt = Quantity[Literal["1000 kilogram * meter ** 2 / ampere / second ** 3"]]
ohm = Quantity[Literal["kilogram * meter ** 2 / ampere ** 2 / second ** 3"]]
siemens = Quantity[Literal["ampere ** 2 * second ** 3 / kilogram / meter ** 2"]]
farad = Quantity[Literal["ampere ** 2 * second ** 4 / kilogram / meter ** 2"]]
henry = Quantity[Literal["kilogram * meter ** 2 / ampere ** 2 / second ** 2"]]
tesla = Quantity[Literal["kilogram / ampere / second ** 2"]]
weber = Quantity[Literal["kilogram * meter ** 2 / ampere / second ** 2"]]

# ---------------------------------------------------------------------------
# Amount of substance / luminosity
# ---------------------------------------------------------------------------
mole = Quantity[Literal["mole"]]
millimole = Quantity[Literal["0.001 mole"]]
candela = Quantity[Literal["candela"]]

# ---------------------------------------------------------------------------
# Force / pressure
# ---------------------------------------------------------------------------
newton = Quantity[Literal["kilogram * meter / second ** 2"]]
kilonewton = Quantity[Literal["1000 kilogram * meter / second ** 2"]]
dyne = Quantity[Literal["1e-05 kilogram * meter / second ** 2"]]
pascal = Quantity[Literal["kilogram / meter / second ** 2"]]
kilopascal = Quantity[Literal["1000 kilogram / meter / second ** 2"]]
megapascal = Quantity[Literal["1000000 kilogram / meter / second ** 2"]]
bar = Quantity[Literal["100000 kilogram / meter / second ** 2"]]
millibar = Quantity[Literal["100 kilogram / meter / second ** 2"]]
atmosphere = Quantity[Literal["101325 kilogram / meter / second ** 2"]]

# ---------------------------------------------------------------------------
# Energy / power
# ---------------------------------------------------------------------------
joule = Quantity[Literal["kilogram * meter ** 2 / second ** 2"]]
kilojoule = Quantity[Literal["1000 kilogram * meter ** 2 / second ** 2"]]
megajoule = Quantity[Literal["1000000 kilogram * meter ** 2 / second ** 2"]]
calorie = Quantity[Literal["4.184 kilogram * meter ** 2 / second ** 2"]]
kilocalorie = Quantity[Literal["4184 kilogram * meter ** 2 / second ** 2"]]
electronvolt = Quantity[Literal["1.602176634e-19 kilogram * meter ** 2 / second ** 2"]]
watt = Quantity[Literal["kilogram * meter ** 2 / second ** 3"]]
kilowatt = Quantity[Literal["1000 kilogram * meter ** 2 / second ** 3"]]
megawatt = Quantity[Literal["1000000 kilogram * meter ** 2 / second ** 3"]]

# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------
hertz = Quantity[Literal["1 / second"]]
kilohertz = Quantity[Literal["1000 1 / second"]]
megahertz = Quantity[Literal["1000000 1 / second"]]
gigahertz = Quantity[Literal["1000000000 1 / second"]]

# ---------------------------------------------------------------------------
# Kinematics
# ---------------------------------------------------------------------------
meter_per_second = Quantity[Literal["meter / second"]]
kilometer_per_hour = Quantity[Literal["0.277777777777778 meter / second"]]
meter_per_second_squared = Quantity[Literal["meter / second ** 2"]]

# ---------------------------------------------------------------------------
# Angle
# ---------------------------------------------------------------------------
radian = Quantity[Literal["radian"]]
degree = Quantity[Literal["0.0174532925199433 radian"]]
steradian = Quantity[Literal["radian ** 2"]]

# ---------------------------------------------------------------------------
# Dimensionless (pure ratios, counts)
# ---------------------------------------------------------------------------
dimensionless = Quantity[Literal["dimensionless"]]

# ---------------------------------------------------------------------------
# Information
# ---------------------------------------------------------------------------
byte = Quantity[Literal["8 bit"]]
