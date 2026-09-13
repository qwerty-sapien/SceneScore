"""Fixed ramp and channel components with separate local geometry contracts."""
import math

from .core import Component, Anchor, LocalGeometry, channel_segment
from .math3d import add, mul, rotate

CHANNEL = dict(length_m=2., width_m=.7, thickness_m=.08, wall_m=.05,
               wall_height_m=.4, actor_radius_m=.15)


class Ramp(Component):
    defaults = {**CHANNEL, 'drop_m': .5}

    def describe(self, p):
        start, end = (0., 0., 0.), (p['length_m'], 0., -p['drop_m'])
        boxes, q = channel_segment('ramp', start, end, p['width_m'], p['thickness_m'], p['wall_m'], p['wall_height_m'])
        normal, direction = rotate(q, (0., 0., 1.)), rotate(q, (1., 0., 0.))
        centers = tuple(add(s, mul(normal, p['actor_radius_m'])) for s in (start, end))
        return LocalGeometry(tuple(boxes), Anchor(centers[0], direction, p['width_m']/2, normal),
                             Anchor(centers[1], direction, p['width_m']/2, normal), centers)


class StraightChannel(Ramp):
    defaults = CHANNEL

    def describe(self, p):
        return super().describe({**p, 'drop_m': 0.})


class CurvedChannel(Component):
    defaults = dict(radius_m=1.4, turn_deg=90., segments=8., width_m=.7, thickness_m=.08,
                    wall_m=.05, wall_height_m=.4, actor_radius_m=.15)

    def describe(self, p):
        count = int(p['segments'])
        if count != p['segments'] or not 4 <= count <= 24:
            raise ValueError('curved channel segments must be an integer in 4..24')
        if not 5 <= abs(p['turn_deg']) <= 150:
            raise ValueError('curve turn must have magnitude 5..150 degrees')
        radius, angle = p['radius_m'], math.radians(abs(p['turn_deg']))
        if radius <= p['width_m']/2+p['wall_m']:
            raise ValueError('curve radius must exceed the outside channel half width')
        sign = 1 if p['turn_deg'] > 0 else -1
        points = tuple((radius*math.sin(angle*i/count), sign*radius*(1-math.cos(angle*i/count)), 0.) for i in range(count+1))
        boxes = []
        for i, (a, b) in enumerate(zip(points, points[1:])):
            boxes.extend(channel_segment(f'arc-{i:02d}', a, b, p['width_m'], p['thickness_m'], p['wall_m'], p['wall_height_m'])[0])
        sagitta = radius*(1-math.cos(angle/count/2))
        clearance = p['width_m']/2*math.cos(angle/count/2)-sagitta
        centers = tuple(add(v, (0., 0., p['actor_radius_m'])) for v in points)
        return LocalGeometry(tuple(boxes), Anchor(centers[0], (1., 0., 0.), clearance),
            Anchor(centers[-1], (math.cos(angle), sign*math.sin(angle), 0.), clearance), centers,
            notes=('Segmented fixed OBB channel; facets and internal static welds remain part of the physical model.',),
            approximation_m=sagitta)
