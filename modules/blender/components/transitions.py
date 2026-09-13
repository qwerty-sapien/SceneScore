"""Passive drop and terminal tray; no prescribed motion is generated."""
import math
from .core import Component, Anchor, BoxGeometry, LocalGeometry, channel_segment


class DropTransition(Component):
    defaults = dict(length_m=2., drop_m=.6, upper_ledge_m=.6, gap_m=.5, width_m=.8,
                    thickness_m=.08, wall_m=.05, wall_height_m=.4, actor_radius_m=.15)

    def describe(self, p):
        if p['drop_m'] <= 0 or p['upper_ledge_m']+p['gap_m'] >= p['length_m']:
            raise ValueError('drop requires positive fall height and a nonempty lower landing ledge')
        if p['length_m']-p['upper_ledge_m']-p['gap_m'] <= 2*p['actor_radius_m']:
            raise ValueError('lower landing ledge must fit the complete sphere footprint')
        upper = [(0., 0., p['drop_m']), (p['upper_ledge_m'], 0., p['drop_m'])]
        lower = [(p['upper_ledge_m']+p['gap_m'], 0., 0.), (p['length_m'], 0., 0.)]
        boxes = []
        for name, ends in [('upper', upper), ('lower', lower)]:
            boxes.extend(channel_segment(name, *ends, p['width_m'], p['thickness_m'], p['wall_m'], p['wall_height_m'])[0])
        centers = tuple((s[0], s[1], s[2]+p['actor_radius_m']) for s in (*upper, *lower))
        return LocalGeometry(tuple(boxes), Anchor(centers[0], (1., 0., 0.), p['width_m']/2),
                             Anchor(centers[-1], (1., 0., 0.), p['width_m']/2), centers,
                             notes=('Upper and lower ledges are separated by an unsupported ballistic interval. Landing requires a solved trajectory.',))

    @property
    def feasibility_constraints(self):
        p = self.parameters
        # This estimate only applies to a world-horizontal launch with zero vertical speed.
        time = math.sqrt(2*p['drop_m']/9.81)
        return {**super().feasibility_constraints, 'ballistic_interval': True,
                'horizontal_launch_estimate': {'local_axes_assumption': 'unrotated, zero launch vertical speed',
                    'fall_time_s': time, 'horizontal_speed_range_m_s': [
                        (p['gap_m']+p['actor_radius_m'])/time,
                        (p['length_m']-p['upper_ledge_m']-p['actor_radius_m'])/time]}}


class Catcher(Component):
    defaults = dict(length_m=1.2, width_m=.9, thickness_m=.08, wall_m=.05,
                    wall_height_m=.5, actor_radius_m=.15)

    def describe(self, p):
        if p['length_m'] <= 3*p['actor_radius_m']:
            raise ValueError('catcher must have room for a sphere beyond its entry')
        boxes, _ = channel_segment('tray', (0., 0., 0.), (p['length_m'], 0., 0.), p['width_m'],
                                   p['thickness_m'], p['wall_m'], p['wall_height_m'])
        boxes.append(BoxGeometry('end-wall', (p['length_m']+p['wall_m']/2, 0., p['wall_height_m']/2),
                                 (p['wall_m']/2, p['width_m']/2+p['wall_m'], p['wall_height_m']/2)))
        centers = ((0., 0., p['actor_radius_m']), (p['length_m']-1.5*p['actor_radius_m'], 0., p['actor_radius_m']))
        return LocalGeometry(tuple(boxes), Anchor(centers[0], (1., 0., 0.), p['width_m']/2),
                             Anchor(centers[1], (1., 0., 0.), p['width_m']/2), centers,
                             notes=('Exit anchor is a terminal sphere-center target inside the tray, not a through port. Retention and settling require simulation.',))

    @property
    def feasibility_constraints(self):
        return {**super().feasibility_constraints, 'terminal_only': True}
