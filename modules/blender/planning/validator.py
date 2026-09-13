"""Conservative pre-construction screening; no trajectory/production certification."""
import copy
import hashlib
import itertools
import json
import math
import statistics

from jsonschema import Draft202012Validator

from modules.blender.scene_intent import SceneIntent, IntentValidationError
from .contracts import SCHEMA, TYPE_MAP, RESOLVED_VERSION, compile_success, compile_failures

VERSION = 'scene-plan-validator-1'
BACKEND = 'fixed-obb-sphere-mechanics-1'
WARNING_POLICY = {'planar_relative_thickness': .05, 'event_cluster_relative_span': .25,
                  'uniform_gap_coefficient_of_variation': .1, 'weak_ending_speed_m_s': .2}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _spatial_metrics(points):
    span = max((math.dist(a, b) for a, b in itertools.combinations(points, 2)), default=0.)
    normal, length = (0., 0., 0.), 0.
    origin = points[0]
    for a, b in itertools.combinations(points[1:], 2):
        u, v = [a[i]-origin[i] for i in range(3)], [b[i]-origin[i] for i in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        size = math.hypot(*cross)
        if size > length:
            normal, length = cross, size
    thickness = max((abs(sum(normal[i]*(p[i]-origin[i]) for i in range(3)))/length for p in points), default=0.) if length else 0.
    return {'span_m': span, 'plane_thickness_m': thickness,
            'axis_extents_m': [max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]}


def validate_plan(document):
    errors, warnings = [], []
    def issue(code, message, path='', *, warning=False):
        (warnings if warning else errors).append({'code': code, 'path': path, 'message': message})
    report = {'schema_version': 'scene-plan-validation-1', 'validator_version': VERSION,
              'status': 'FAILED', 'errors': errors, 'warnings': warnings, 'metrics': {},
              'scope': 'Authoring feasibility screening; simulation, contact certification and visual review still required.',
              'physics_validated': False, 'approval': None, 'warning_policy': WARNING_POLICY.copy()}
    blocked = {'schema_version': RESOLVED_VERSION, 'status': 'BLOCKED', 'constraints': None}
    try:
        digest = canonical_hash(document)
        report['input_sha256'] = digest
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        issue('INVALID_JSON_VALUE', str(error))
        return report, blocked
    schema_errors = sorted(Draft202012Validator(SCHEMA).iter_errors(document), key=lambda e: str(list(e.path)))
    if schema_errors:
        for error in schema_errors[:30]:
            issue('INVALID_STRUCTURE', error.message, '.'.join(map(str, error.path)))
        if isinstance(document, dict) and document.get('schema_version') == 'scene-intent-2':
            issue('A3_INTENT_REQUIRES_RESOLUTION', 'Wrap the abstract intent with numeric event conditions, route start/terminal and a motion contract.')
        return report, blocked
    raw = copy.deepcopy(document)
    try:
        intent = SceneIntent.from_dict(raw['intent'])
    except IntentValidationError as error:
        # A4 explicitly makes incomplete camera exposure a soft warning. A local
        # validation copy checks all other A3 invariants; the input is never changed.
        camera_message = 'camera must intend coverage of every salient event'
        if str(error) == camera_message:
            validation_copy = copy.deepcopy(raw['intent'])
            validation_copy['camera']['readable_event_ids'] = [e['id'] for e in validation_copy['events']]
            try:
                intent = SceneIntent.from_dict(validation_copy)
            except IntentValidationError as nested:
                issue('ABSTRACT_INTENT_INVALID', str(nested), 'intent')
                return report, blocked
            issue('CAMERA_INTERACTION_HIDDEN', camera_message, 'intent.camera', warning=True)
        else:
            issue('ABSTRACT_INTENT_INVALID', str(error), 'intent')
            return report, blocked
    actors = {a.id: a for a in intent.actors}
    moving = [a for a in intent.actors if a.motion != 'fixed']
    if intent.mechanics.backend != BACKEND or len(moving) != 1 or moving[0].shape != 'sphere' or moving[0].motion != 'dynamic':
        issue('UNSUPPORTED_MECHANICS', 'This gate supports one dynamic sphere against fixed OBB geometry only.', 'intent.mechanics')
    if tuple(intent.mechanics.gravity_m_s2) != (0., 0., -9.81):
        issue('UNSUPPORTED_GRAVITY', 'The declared analytic implementation uses world Z gravity (0,0,-9.81) m/s².', 'intent.mechanics.gravity_m_s2')
    if any(a.motion != 'fixed' for a in intent.actors if a not in moving) or any(a.motion == 'prescribed' for a in intent.actors):
        issue('UNVALIDATED_ACTUATION', 'Motor-driven collision geometry is outside this fixed-geometry scope.')
    motion = raw['motion_contract']
    if motion['trajectory_source'] != 'analytic_solver' or motion['post_release_animation'] not in {'none', 'solver_replay'}:
        issue('TRAJECTORY_OVERRIDE', 'Post-release motion must come from the analytic solver; manual keyframes are not physics.', 'motion_contract')
    if motion['teleportation'] or motion['overrides_after_release']:
        issue('HIDDEN_TELEPORT_OR_CONTROL', 'Teleportation and post-release pose/velocity overrides are forbidden.', 'motion_contract')
    radius = motion['actor_radius_m']
    if not 0 < radius <= 10:
        issue('INVALID_ACTOR_RADIUS', 'actor_radius_m must be in (0,10].')
    if any(not 0 <= value <= 1 for value in motion['sphere_material'].values()):
        issue('INVALID_MATERIAL', 'Sphere restitution/friction/rolling resistance must be within [0,1].')
    actor_id = moving[0].id if len(moving) == 1 else None
    route, start, terminal = raw['route'], raw['route']['start'], raw['route']['terminal']
    if start['actor'] != actor_id or terminal['actor'] != actor_id:
        issue('ROUTE_ACTOR_MISMATCH', 'Start and terminal state must belong to the one dynamic sphere.')
    for label, key, state in [('start', 'support', start), ('terminal', 'target', terminal)]:
        target = actors.get(state[key])
        if target is None or target.motion != 'fixed' or not target.collision_enabled:
            issue('UNDEFINED_' + label.upper(), 'Start/terminal requires an existing fixed physical support.', 'route.' + label)
    if terminal['target'] not in intent.ending.support_ids or not 0 <= terminal['speed_max_m_s'] <= 1:
        issue('TERMINAL_CONTRADICTION', 'Terminal target/speed contradicts the declared supported ending.', 'route.terminal')
    stage_positions = {s['stage_id']: s['position_m'] for s in route['stages']}
    if len(stage_positions) != len(route['stages']) or list(stage_positions) != [s.id for s in intent.route_stages]:
        issue('ROUTE_STAGE_MISMATCH', 'Numeric route stages must occur once in the abstract route order.')
    planned = {e['id']: e for e in raw['events']}
    abstract = {e.id: e for e in intent.events}
    if len(planned) != len(raw['events']) or set(planned) != set(abstract):
        issue('EVENT_ID_MISMATCH', 'Event contracts must cover each abstract event exactly once.')
    resolved_events = []
    indices = {name: i for i, name in enumerate(intent.event_order)}
    for event in raw['events']:
        name = event['id']
        base = abstract.get(name)
        if base is None:
            continue
        if TYPE_MAP.get(base.kind) != event['type']:
            issue('UNSUPPORTED_EVENT', 'Event type contradicts the abstract event or requires an unsupported material model.', name)
        if event['actor'] != actor_id or event['actor'] not in base.actor_ids:
            issue('EVENT_ACTOR_MISMATCH', 'Every salient event must use the declared dynamic sphere.', name)
        target = event['target']
        expected_targets = set(base.actor_ids) - {event['actor']}
        if ({target} if target is not None else set()) != expected_targets:
            issue('EVENT_TARGET_MISMATCH', 'Event target must match the abstract physical participant.', name)
        if target is not None and (target not in actors or actors[target].motion != 'fixed' or not actors[target].collision_enabled):
            issue('UNKNOWN_OR_MOVING_TARGET', 'Event target must be an existing fixed collider.', name)
        after = event['after']
        after = [] if after is None else [after] if isinstance(after, str) else after
        if len(set(after)) != len(after) or any(ref not in indices or indices[ref] >= indices[name] for ref in after):
            issue('EVENT_ORDER_CONTRADICTION', 'after dependencies are unknown, cyclic or contradict the declared event order.', name)
        window = event['time_window']
        if not (base.target_window.start_s <= window[0] < window[1] <= base.target_window.end_s):
            issue('EVENT_WINDOW_CONTRADICTION', 'Resolved event window must be inside the abstract target window.', name)
        necessary_failures = {'success_condition_not_met', 'missed_time_window', 'unphysical_motion'}
        if not necessary_failures <= set(event['failure_conditions']) or len(set(event['failure_conditions'])) != len(event['failure_conditions']):
            issue('FAILURE_CRITERIA_MISSING', 'Declare success failure, missed window and unphysical motion, each once.', name)
        try:
            predicates = compile_success(event)
        except ValueError as error:
            issue('UNMEASURABLE_EVENT', str(error), name)
            continue
        if event['type'] == 'near_miss' and base.clearance is not None:
            gap = event['success_condition']['surface_clearance_m']
            if gap['min'] < base.clearance.minimum_m or gap['max'] > base.clearance.maximum_m:
                issue('CLEARANCE_CONTRADICTION', 'Resolved clearance must refine the abstract physical range.', name)
        if event['type'] == 'supported_catch' and event['success_condition']['supported_duration_min_s'] > window[1]-window[0]:
            issue('CATCH_WINDOW_TOO_SHORT', 'Required support duration exceeds the event window.', name)
        resolved_events.append({'id': name, 'type': event['type'], 'actor': event['actor'], 'target': target,
            'after': after, 'time_window_s': window, 'position_hint_m': stage_positions.get(base.stage_id),
            'success_all': predicates, 'failure_any': compile_failures(event, predicates),
            'music_salience': event['music_salience'], 'emit_once_per_episode': True,
            'foley_eligible': event['type'] == 'salient_collision', 'measurement_status': 'NOT_MEASURED'})
    ordered_events = [planned[name] for name in intent.event_order if name in planned]
    gaps = [b['time_window'][0]-a['time_window'][1] for a, b in zip(ordered_events, ordered_events[1:])]
    if any(g < intent.salience_policy.minimum_gap_s-1e-9 for g in gaps):
        issue('SALIENCE_SPACING', 'Event windows overlap or violate the declared sparse spacing.')
    duty = sum(e['time_window'][1]-e['time_window'][0] for e in ordered_events)/intent.duration_s
    if duty > intent.salience_policy.maximum_duty_cycle+1e-9:
        issue('SALIENCE_DUTY', 'Resolved salient windows exceed the declared duty cycle.')
    points = [start['position_m'], *[s['position_m'] for s in route['stages']], terminal['position_m']]
    metrics = _spatial_metrics(points)
    max_drop = start['position_m'][2]-min(p[2] for p in points)
    max_speed = math.sqrt(math.hypot(*start['velocity_m_s'])**2+2*9.81*max(0, max_drop))
    energy_ceiling_z = start['position_m'][2]+math.hypot(*start['velocity_m_s'])**2/(2*9.81)
    if any(p[2] > energy_ceiling_z+1e-9 for p in points):
        issue('INSUFFICIENT_GRAVITATIONAL_ENERGY', 'Requested route exceeds the initial mechanical-energy height bound.')
    for event in resolved_events:
        if event['position_hint_m'] is None:
            continue
        energy_speed = math.sqrt(max(0, math.hypot(*start['velocity_m_s'])**2+2*9.81*(start['position_m'][2]-event['position_hint_m'][2])))
        for predicate in event['success_all']:
            if predicate['metric'] == 'speed_gain_m_s' and predicate['value'] > energy_speed+1e-9:
                issue('INFEASIBLE_SPEED_GAIN', 'Requested gain exceeds the lossless gravitational speed upper bound.', event['id'])
        lower_time = math.dist(start['position_m'], event['position_hint_m'])/max_speed if max_speed else math.inf
        if lower_time >= event['time_window_s'][1]:
            issue('UNREACHABLE_EVENT_DEADLINE', 'Even the conservative distance/speed lower bound misses the event deadline.', event['id'])
    if metrics['span_m'] == 0 or metrics['plane_thickness_m'] <= metrics['span_m']*WARNING_POLICY['planar_relative_thickness']:
        issue('NEARLY_PLANAR_ROUTE', 'Route anchor geometry is nearly planar/linear; consider depth and elevation variety.', warning=True)
    event_points = [e['position_hint_m'] for e in resolved_events if e['position_hint_m'] is not None]
    event_span = _spatial_metrics(event_points)['span_m'] if event_points else 0.
    if event_span <= max(.25, metrics['span_m']*WARNING_POLICY['event_cluster_relative_span']):
        issue('EVENTS_SPATIALLY_CLUSTERED', 'Important events occupy one small region relative to the route.', warning=True)
    if len(gaps) >= 2 and statistics.mean(gaps) > 0 and statistics.pstdev(gaps)/statistics.mean(gaps) < WARNING_POLICY['uniform_gap_coefficient_of_variation']:
        issue('UNIFORM_EVENT_SPACING', 'Event spacing is nearly uniform; review phrasing variety.', warning=True)
    if not intent.ending.keep_visible or terminal['speed_max_m_s'] > WARNING_POLICY['weak_ending_speed_m_s']:
        issue('VISUALLY_WEAK_ENDING', 'Ending visibility or intended settling speed may weaken the terminal beat.', warning=True)
    if actor_id not in raw['intent']['camera']['focus_actor_ids']:
        issue('CAMERA_INTERACTION_HIDDEN', 'Camera focus omits the dynamic actor.', warning=True)
    report['metrics'] = {**metrics, 'event_span_m': event_span, 'event_gaps_s': gaps, 'salient_duty_cycle': duty,
                         'lossless_speed_upper_bound_m_s': max_speed, 'simulation_performed': False}
    checks = ['coherent_sequence', 'supported_mechanics', 'sparse_events', 'measurable_criteria', 'defined_route', 'sparse_music_mapping']
    # All six answers require a coherent whole plan; errors remain individually located.
    report['answers'] = {key: 'NO' if errors else 'YES_AT_PLANNING_LEVEL' for key in checks}
    if errors:
        return report, blocked
    report['status'] = 'PASSED'
    ordered = {e['id']: e for e in resolved_events}
    constraints = {'backend': BACKEND, 'dynamic_actor': actor_id, 'actor_radius_m': radius,
        'gravity_m_s2': [0., 0., -9.81], 'sphere_material': motion['sphere_material'],
        'collision_geometry': 'fixed_obb_union', 'maximum_colliders': 128,
        'motion_source': 'analytic_solver', 'allow_teleportation': False, 'allow_post_release_overrides': False,
        'replay_requires_solver_trace': True, 'route': route, 'duration_s': intent.duration_s,
        'actors': raw['intent']['actors'], 'events': [ordered[name] for name in intent.event_order],
        'continuous_support': raw['intent']['support_contacts'], 'camera_intent': raw['intent']['camera'],
        'ending_intent': raw['intent']['ending'], 'music_hints': raw['intent']['music_hints'],
        'support_contact_music_policy': 'retain_raw_do_not_emit_per_sample',
        'required_later_gates': ['parameter_solution', 'independent_physical_validation', 'contact_certificates',
                                 'fresh_process_replay', 'full_motion_camera_review', 'exact_human_approval']}
    resolved = {'schema_version': RESOLVED_VERSION, 'status': 'READY_FOR_CONSTRUCTION',
                'input_sha256': digest, 'validator_version': VERSION, 'constraints': constraints, 'source_plan': raw}
    resolved['sha256'] = canonical_hash(resolved)
    report['resolved_constraints_sha256'] = resolved['sha256']
    return report, resolved


def verify_resolved(resolved):
    """Recompute from bound source before a builder consumes a stored result."""
    if not isinstance(resolved, dict) or resolved.get('status') != 'READY_FOR_CONSTRUCTION':
        raise ValueError('resolved constraints are blocked or malformed')
    report, expected = validate_plan(resolved.get('source_plan'))
    if report['status'] != 'PASSED' or expected != resolved:
        raise ValueError('resolved constraints are stale, edited or inconsistent with their source plan')
    return copy.deepcopy(resolved['constraints'])
