"""Reusable flat support and structural frame geometry."""
from .core import Component, Anchor, BoxGeometry, LocalGeometry, channel_segment


class Platform(Component):
    defaults = dict(length_m=2., width_m=1.2, thickness_m=.12, actor_radius_m=.15)

    def describe(self, p):
        boxes, _ = channel_segment('platform', (0., 0., 0.), (p['length_m'], 0., 0.), p['width_m'], p['thickness_m'], 0., 0.)
        centers = ((0., 0., p['actor_radius_m']), (p['length_m'], 0., p['actor_radius_m']))
        return LocalGeometry(tuple(boxes), Anchor(centers[0], (1., 0., 0.), p['width_m']/2),
                             Anchor(centers[1], (1., 0., 0.), p['width_m']/2), centers,
                             notes=('No lateral guide walls; lateral retention requires trajectory validation.',))


class SupportFrame(Component):
    defaults = dict(length_m=2., width_m=1.2, height_m=2., beam_m=.1, actor_radius_m=.15)

    def describe(self, p):
        length, w, h, b = (p[k] for k in ('length_m', 'width_m', 'height_m', 'beam_m'))
        if 2*b >= min(length, w, h):
            raise ValueError('frame beams must fit inside frame dimensions')
        boxes = [BoxGeometry(f'leg-{i}-{j}', (x, y, -h/2), (b/2, b/2, h/2))
                 for i, x in enumerate((b/2, length-b/2)) for j, y in enumerate((-w/2+b/2, w/2-b/2))]
        boxes.extend(BoxGeometry(f'beam-{i}', (length/2, y, -b/2), (length/2, b/2, b/2))
                     for i, y in enumerate((-w/2+b/2, w/2-b/2)))
        centers = ((0., 0., p['actor_radius_m']), (length, 0., p['actor_radius_m']))
        return LocalGeometry(tuple(boxes), Anchor(centers[0], (1., 0., 0.), w/2-b),
                             Anchor(centers[1], (1., 0., 0.), w/2-b), centers, route_capable=False,
                             notes=('Structural attachment anchors; this open frame is not a sphere travel surface.',))
