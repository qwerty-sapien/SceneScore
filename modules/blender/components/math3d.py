"""Dependency-free rigid transforms in world XYZ metres, quaternion xyzw."""
import itertools
import math


def finite(value, label):
    if type(value) not in (int, float):
        raise ValueError(label + ' must be a finite number, not a boolean')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(label + ' is too large') from error
    if not math.isfinite(number) or abs(number) > 1e6:
        raise ValueError(label + ' must be finite and bounded to 1e6')
    return number


def vector(value, label='vector', count=3):
    if not isinstance(value, (list, tuple)) or len(value) != count:
        raise ValueError(f'{label} must contain {count} numbers')
    return tuple(finite(x, label) for x in value)


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def mul(a, scale):
    return tuple(x*scale for x in a)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(v):
    length = math.hypot(*v)
    if length < 1e-12:
        raise ValueError('zero direction')
    return mul(v, 1/length)


def quaternion(q):
    q = vector(q, 'quaternion_xyzw', 4)
    size = math.hypot(*q)
    if abs(size-1) > 1e-6:
        raise ValueError('quaternion must be unit length; transforms do not support scale/shear')
    q = mul(q, 1/size)
    # q and -q serialize identically, including 180-degree rotations.
    sign = next((1 if x > 0 else -1 for x in reversed(q) if abs(x) > 1e-12), 1)
    return tuple(0. if abs(x) < 1e-15 else x for x in mul(q, sign))


def qmul(a, b):
    return (*add(add(mul(b[:3], a[3]), mul(a[:3], b[3])), cross(a[:3], b[:3])), a[3]*b[3]-dot(a[:3], b[:3]))


def axis_angle(axis, radians):
    return (*mul(unit(axis), math.sin(radians/2)), math.cos(radians/2))


def rotate(q, v):
    t = mul(cross(q[:3], v), 2)
    return add(v, add(mul(t, q[3]), cross(q[:3], t)))


def direction_angle_deg(a, b):
    return math.degrees(math.acos(max(-1., min(1., dot(unit(a), unit(b))))))


def forward_rotation(direction):
    d = unit(direction)
    yaw, pitch = math.atan2(d[1], d[0]), math.atan2(-d[2], math.hypot(d[0], d[1]))
    return quaternion(qmul(axis_angle((0, 0, 1), yaw), axis_angle((0, 1, 0), pitch)))


def corners(center, half, q):
    return tuple(add(center, rotate(q, tuple(h*s for h, s in zip(half, signs))))
                 for signs in itertools.product((-1, 1), repeat=3))


def bounds(points):
    if not points:
        raise ValueError('bounds require geometry')
    return {'minimum_m': tuple(min(p[i] for p in points) for i in range(3)),
            'maximum_m': tuple(max(p[i] for p in points) for i in range(3))}
