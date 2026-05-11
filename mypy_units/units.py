"""Pre-defined unit type aliases.

Import individual names and use them directly as type annotations::

    from mypy_units.units import meter, second, meter_per_second

    def speed(d: meter, t: second) -> meter_per_second: ...

Each alias is a unit-specific name for a ``Quantity`` of a given physical
dimension. Units of the same dimension are mutually compatible as function
arguments. Arithmetic results propagate dimension information so that the
mypy plugin can detect mismatches in function bodies and at call sites.
"""
from __future__ import annotations

from typing import Literal

from mypy_units.quantity import Quantity

# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------
meter = Quantity[Literal["[length]"]]
kilometer = Quantity[Literal["[length]"]]
centimeter = Quantity[Literal["[length]"]]
millimeter = Quantity[Literal["[length]"]]
micrometer = Quantity[Literal["[length]"]]
nanometer = Quantity[Literal["[length]"]]
mile = Quantity[Literal["[length]"]]
yard = Quantity[Literal["[length]"]]
foot = Quantity[Literal["[length]"]]
inch = Quantity[Literal["[length]"]]
nautical_mile = Quantity[Literal["[length]"]]
angstrom = Quantity[Literal["[length]"]]
light_year = Quantity[Literal["[length]"]]

# ---------------------------------------------------------------------------
# Area / volume
# ---------------------------------------------------------------------------
square_meter = Quantity[Literal["[length] ** 2"]]
cubic_meter = Quantity[Literal["[length] ** 3"]]
hectare = Quantity[Literal["[length] ** 2"]]
liter = Quantity[Literal["[length] ** 3"]]
milliliter = Quantity[Literal["[length] ** 3"]]

# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------
second = Quantity[Literal["[time]"]]
millisecond = Quantity[Literal["[time]"]]
microsecond = Quantity[Literal["[time]"]]
nanosecond = Quantity[Literal["[time]"]]
minute = Quantity[Literal["[time]"]]
hour = Quantity[Literal["[time]"]]
day = Quantity[Literal["[time]"]]
week = Quantity[Literal["[time]"]]
year = Quantity[Literal["[time]"]]

# ---------------------------------------------------------------------------
# Mass
# ---------------------------------------------------------------------------
kilogram = Quantity[Literal["[mass]"]]
gram = Quantity[Literal["[mass]"]]
milligram = Quantity[Literal["[mass]"]]
microgram = Quantity[Literal["[mass]"]]
tonne = Quantity[Literal["[mass]"]]
pound = Quantity[Literal["[mass]"]]
ounce = Quantity[Literal["[mass]"]]

# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------
kelvin = Quantity[Literal["[temperature]"]]
degC = Quantity[Literal["[temperature]"]]
degF = Quantity[Literal["[temperature]"]]

# ---------------------------------------------------------------------------
# Electric
# ---------------------------------------------------------------------------
ampere = Quantity[Literal["[current]"]]
milliampere = Quantity[Literal["[current]"]]
volt = Quantity[Literal["[length] ** 2 * [mass] / [current] / [time] ** 3"]]
millivolt = Quantity[Literal["[length] ** 2 * [mass] / [current] / [time] ** 3"]]
kilovolt = Quantity[Literal["[length] ** 2 * [mass] / [current] / [time] ** 3"]]
ohm = Quantity[Literal["[length] ** 2 * [mass] / [current] ** 2 / [time] ** 3"]]
siemens = Quantity[Literal["[current] ** 2 * [time] ** 3 / [length] ** 2 / [mass]"]]
farad = Quantity[Literal["[current] ** 2 * [time] ** 4 / [length] ** 2 / [mass]"]]
henry = Quantity[Literal["[length] ** 2 * [mass] / [current] ** 2 / [time] ** 2"]]
tesla = Quantity[Literal["[mass] / [current] / [time] ** 2"]]
weber = Quantity[Literal["[length] ** 2 * [mass] / [current] / [time] ** 2"]]

# ---------------------------------------------------------------------------
# Amount of substance / luminosity
# ---------------------------------------------------------------------------
mole = Quantity[Literal["[substance]"]]
millimole = Quantity[Literal["[substance]"]]
candela = Quantity[Literal["[luminosity]"]]

# ---------------------------------------------------------------------------
# Force / pressure
# ---------------------------------------------------------------------------
newton = Quantity[Literal["[length] * [mass] / [time] ** 2"]]
kilonewton = Quantity[Literal["[length] * [mass] / [time] ** 2"]]
dyne = Quantity[Literal["[length] * [mass] / [time] ** 2"]]
pascal = Quantity[Literal["[mass] / [length] / [time] ** 2"]]
kilopascal = Quantity[Literal["[mass] / [length] / [time] ** 2"]]
megapascal = Quantity[Literal["[mass] / [length] / [time] ** 2"]]
bar = Quantity[Literal["[mass] / [length] / [time] ** 2"]]
millibar = Quantity[Literal["[mass] / [length] / [time] ** 2"]]
atmosphere = Quantity[Literal["[mass] / [length] / [time] ** 2"]]

# ---------------------------------------------------------------------------
# Energy / power
# ---------------------------------------------------------------------------
joule = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
kilojoule = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
megajoule = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
calorie = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
kilocalorie = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
electronvolt = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 2"]]
watt = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 3"]]
kilowatt = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 3"]]
megawatt = Quantity[Literal["[length] ** 2 * [mass] / [time] ** 3"]]

# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------
hertz = Quantity[Literal["1 / [time]"]]
kilohertz = Quantity[Literal["1 / [time]"]]
megahertz = Quantity[Literal["1 / [time]"]]
gigahertz = Quantity[Literal["1 / [time]"]]

# ---------------------------------------------------------------------------
# Kinematics
# ---------------------------------------------------------------------------
meter_per_second = Quantity[Literal["[length] / [time]"]]
kilometer_per_hour = Quantity[Literal["[length] / [time]"]]
meter_per_second_squared = Quantity[Literal["[length] / [time] ** 2"]]

# ---------------------------------------------------------------------------
# Angle
# ---------------------------------------------------------------------------
radian = Quantity[Literal["dimensionless"]]
degree = Quantity[Literal["dimensionless"]]
steradian = Quantity[Literal["dimensionless"]]

# ---------------------------------------------------------------------------
# Information
# ---------------------------------------------------------------------------
byte = Quantity[Literal["dimensionless"]]
