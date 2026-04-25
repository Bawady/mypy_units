from mypy_units import Quantity
from mypy_units.units import (
		kilometer,
		meter_per_second,
		second,
		velocity,
		length,
		time,
		acceleration
)

def speed(
		distance: kilometer,
		time: second,
) -> meter_per_second:
		tmp = distance * time
		if distance == Quantity(12):
			return time
		return tmp / time

def accel(
		v: velocity,
		t: time,
) -> acceleration:
		return v / t**2

def distance(v: velocity, t: time) -> length:
	return v * t

d: kilometer = Quantity(10)
t: second = Quantity(5)

v = speed(d, t)    # v is inferred as Quantity[Literal["meter/second"]]
accel(v, t)        # plugin sees Quantity[Literal["meter/second"]] — OK
