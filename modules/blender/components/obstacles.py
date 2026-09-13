"""Fixed interaction targets; ports express hypotheses, never forced trajectories."""
import math
from .core import Component, Anchor, BoxGeometry, LocalGeometry
from .math3d import add, sub, mul, axis_angle


class FixedDeflector(Component):
    defaults = dict(deflection_deg=90., panel_length_m=1.4, panel_height_m=.6, panel_thickness_m=.08,
                    approach_length_m=1., deck_margin_m=.5, deck_thickness_m=.1, actor_radius_m=.15)

    def describe(self, p):
        if not 20 <= p['deflection_deg'] <= 140:
            raise ValueError('deflector angle must be 20..140 degrees')
        if p['panel_height_m'] < 2*p['actor_radius_m']:
            raise ValueError('deflector panel must cover the sphere for the nominal horizontal interaction')
        theta = math.radians(p['deflection_deg'])
        # Account for the finite panel half-thickness as well as sphere radius.
        contact = (-(p['actor_radius_m']+p['panel_thickness_m']/2)/math.sin(theta/2), 0., p['actor_radius_m'])
        if abs(contact[0]*math.cos(theta/2)) >= p['panel_length_m']/2:
            raise ValueError('nominal sphere contact lies beyond the finite deflector panel')
        outgoing = (math.cos(theta), math.sin(theta), 0.)
        entry = sub(contact, (p['approach_length_m'], 0., 0.))
        exit = add(contact, mul(outgoing, p['approach_length_m']))
        minx = min(entry[0], exit[0], -p['panel_length_m']/2)-p['deck_margin_m']
        maxx = max(entry[0], exit[0], p['panel_length_m']/2)+p['deck_margin_m']
        miny = min(entry[1], exit[1], -p['panel_length_m']/2)-p['deck_margin_m']
        maxy = max(entry[1], exit[1], p['panel_length_m']/2)+p['deck_margin_m']
        boxes = (BoxGeometry('panel', (0., 0., p['panel_height_m']/2),
                             (p['panel_length_m']/2, p['panel_thickness_m']/2, p['panel_height_m']/2), axis_angle((0., 0., 1.), theta/2)),
                 BoxGeometry('deck', ((minx+maxx)/2, (miny+maxy)/2, -p['deck_thickness_m']/2),
                             ((maxx-minx)/2, (maxy-miny)/2, p['deck_thickness_m']/2)))
        return LocalGeometry(boxes, Anchor(entry, (1., 0., 0.), p['deck_margin_m']),
                             Anchor(exit, outgoing, p['deck_margin_m']), (entry, contact, exit),
                             notes=('Ports use the frictionless elastic reflection direction. Actual restitution, friction and spin require solving; no velocity is prescribed.',))


class ClearancePost(Component):
    defaults = dict(post_width_m=.18, post_depth_m=.18, post_height_m=.8,
                    path_offset_m=.28, approach_length_m=1.2, actor_radius_m=.15)

    def describe(self, p):
        clearance = p['path_offset_m']-p['post_depth_m']/2
        if clearance <= p['actor_radius_m']:
            raise ValueError('clearance post requires a positive physical surface gap to the sphere')
        if p['post_height_m'] < p['actor_radius_m']:
            raise ValueError('post must reach the sphere center for the declared horizontal surface clearance')
        centers = ((-p['approach_length_m']/2, p['path_offset_m'], p['actor_radius_m']),
                   (p['approach_length_m']/2, p['path_offset_m'], p['actor_radius_m']))
        return LocalGeometry((BoxGeometry('post', (0., 0., p['post_height_m']/2),
                                          (p['post_width_m']/2, p['post_depth_m']/2, p['post_height_m']/2)),),
                             Anchor(centers[0], (1., 0., 0.), clearance), Anchor(centers[1], (1., 0., 0.), clearance),
                             centers, route_capable=False,
                             notes=('Interaction path requires external support or a ballistic solution; post alone provides no floor.',))

    @property
    def feasibility_constraints(self):
        p = self.parameters
        return {**super().feasibility_constraints,
                'nominal_surface_clearance_m': p['path_offset_m']-p['post_depth_m']/2-p['actor_radius_m']}
