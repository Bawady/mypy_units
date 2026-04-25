# mypy-units

A [mypy](https://mypy.readthedocs.io/) plugin that catches physical-unit dimension mismatches at static analysis time. Annotate function parameters and return types with unit aliases or `Quantity[Literal["..."]]` and mypy will reject calls where the dimensions don't match — including across chained function calls and through arithmetic inside function bodies.

```
error: Dimension mismatch for argument 'time': expected [time], got [length]
error: Incompatible return value type (got "Quantity[Literal['[length]']]",
       expected "Quantity[Literal['[length] / [time]']]")
```

Supports both [Pint](https://pint.readthedocs.io/) and [pintrs](https://github.com/BioDisCo/pintrs) (a Rust rewrite of Pint) as the unit registry backend.

---

## Installation

```bash
pip install mypy-units            # uses pint, scalar floats only
pip install mypy-units[numpy]     # adds numpy array support
pip install mypy-units pintrs     # use pintrs as the backend
```

Enable the plugin in your mypy configuration:

**`pyproject.toml`**
```toml
[tool.mypy]
plugins = ["mypy_units.plugin"]
```

**`mypy.ini`**
```ini
[mypy]
plugins = mypy_units.plugin
```

---

## Annotation styles

### Recommended: unit aliases

Import pre-defined aliases from `mypy_units.units`. Each alias is a
`TypeAlias` for `Quantity[Literal["<pint-dimensionality>"]]`:

```python
from mypy_units import Quantity
from mypy_units.units import meter, meter_per_second, second

def speed(distance: meter, time: second) -> meter_per_second:
	return distance / time

d: meter = Quantity(10)
t: second    = Quantity(5)
v = speed(d, t)  # v: meter_per_second
```

Generic dimension aliases are also available for unit-agnostic annotations:

```python
from mypy_units.units import length, time, velocity, acceleration

def speed(distance: length, time: time) -> velocity: ...
def accel(v: velocity, t: time) -> acceleration: ...
```

Full list of aliases: length, area, volume, time, mass, temperature, current,
substance, luminosity, velocity, acceleration, force, pressure, energy, power,
frequency, dimensionless — plus named-unit aliases such as `meter`, `kilometer`,
`second`, `kilogram`, `newton`, `pascal`, `joule`, `watt`, `volt`, …

### Alternative: inline `Quantity[Literal["..."]]`

For any unit or dimensionality not covered by the aliases:

```python
from typing import Literal
from mypy_units import Quantity

density: Quantity[Literal["[mass] / [length] ** 3"]]
```

The Literal string can be a **pint unit string** (`"meter/second"`) or a
**pint dimensionality string** (`"[length] / [time]"`). Any two annotations
whose Pint dimensionalities are equal are considered compatible.

---

## NumPy array support

Unit aliases work for numpy arrays without any change to annotations — wrap the
array in `Quantity` and the same dimension checking applies:

```python
import numpy as np
from mypy_units import Quantity
from mypy_units.units import kilometer, second, meter_per_second

def speed(distance: kilometer, t: second) -> meter_per_second:
	return distance / t

# scalar
d: kilometer = Quantity(10.0)
t: second    = Quantity(2.0)
v = speed(d, t)
print(v.value)  # 5.0

# numpy arrays — same annotation, same check
d_arr: kilometer = Quantity(np.array([10.0, 20.0, 30.0]))
t_arr: second    = Quantity(np.array([2.0, 4.0, 5.0]))
v_arr = speed(d_arr, t_arr)
print(v_arr.value)  # [5. 5. 6.]
```

Passing a `second`-tagged array where `kilometer` is expected is still caught:

```python
speed(t_arr, t_arr)
# error: Dimension mismatch for argument 'distance': expected [length], got [time]
```

