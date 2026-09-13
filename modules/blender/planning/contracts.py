"""Structural contract and measurable event predicates for authoring plans."""
VERSION = 'scene-feasibility-plan-1'
RESOLVED_VERSION = 'scene-resolved-constraints-1'
TYPE_MAP = {'acceleration': 'acceleration_phase', 'deceleration': 'deceleration_phase',
            'collision': 'salient_collision', 'bounce': 'salient_collision', 'graze': 'salient_collision',
            'near_miss': 'near_miss', 'release': 'release', 'settle': 'supported_catch'}
FAILURES = ['success_condition_not_met', 'missed_time_window', 'unphysical_motion', 'wrong_target', 'unexpected_contact']


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
            'additionalProperties': False}


def array(items, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}


NUMBER = {'type': 'number'}
TEXT = {'type': 'string', 'minLength': 1}
VECTOR = {'type': 'array', 'items': NUMBER, 'minItems': 3, 'maxItems': 3}
WINDOW = {'type': 'array', 'items': NUMBER, 'minItems': 2, 'maxItems': 2}
SUCCESS = obj({'speed_gain_min': NUMBER, 'speed_loss_min': NUMBER, 'target_contact': {'type': 'boolean'},
               'heading_change_min_deg': NUMBER, 'surface_clearance_m': obj({'min': NUMBER, 'max': NUMBER}),
               'support_released': {'type': 'boolean'}, 'speed_max_m_s': NUMBER,
               'supported_duration_min_s': NUMBER}, required=[])
EVENT = obj({'id': TEXT, 'type': TEXT, 'actor': TEXT, 'target': {'type': ['string', 'null']},
             'after': {'oneOf': [{'type': 'null'}, TEXT, array(TEXT)]}, 'time_window': WINDOW,
             'success_condition': SUCCESS, 'failure_conditions': array({'enum': FAILURES}, 1),
             'music_salience': {'enum': ['primary', 'secondary']}})
SCHEMA = obj({
    'schema_version': {'const': VERSION}, 'intent': {'type': 'object'},
    'motion_contract': obj({'actor_radius_m': NUMBER, 'trajectory_source': TEXT,
                            'post_release_animation': TEXT, 'teleportation': {'type': 'boolean'},
                            'overrides_after_release': array(TEXT),
                            'sphere_material': obj({'restitution': NUMBER, 'friction': NUMBER, 'rolling_resistance': NUMBER})}),
    'route': obj({'start': obj({'actor': TEXT, 'support': TEXT, 'position_m': VECTOR, 'velocity_m_s': VECTOR}),
                  'stages': array(obj({'stage_id': TEXT, 'position_m': VECTOR}), 1),
                  'terminal': obj({'actor': TEXT, 'target': TEXT, 'position_m': VECTOR, 'speed_max_m_s': NUMBER})}),
    'events': array(EVENT, 1),
})
SCHEMA.update({'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': VERSION})


def compile_success(event):
    """Exact metric names/units/operators; no free-text 'looks right' conditions."""
    kind, c = event['type'], event['success_condition']
    required = {
        'acceleration_phase': {'speed_gain_min'}, 'deceleration_phase': {'speed_loss_min'},
        'salient_collision': {'target_contact'}, 'near_miss': {'surface_clearance_m'},
        'release': {'support_released'}, 'supported_catch': {'target_contact', 'speed_max_m_s', 'supported_duration_min_s'},
    }
    if kind not in required:
        raise ValueError('unsupported event type: ' + kind)
    allowed = required[kind] | ({'heading_change_min_deg'} if kind == 'salient_collision' else set())
    if not required[kind] <= c.keys() or not c.keys() <= allowed:
        raise ValueError(f'{kind} requires {sorted(required[kind])}; accepts only {sorted(allowed)}')
    rules = []
    def rule(metric, operator, value, unit):
        rules.append({'metric': metric, 'operator': operator, 'value': value, 'unit': unit})
    for key, metric in [('speed_gain_min', 'speed_gain_m_s'), ('speed_loss_min', 'speed_loss_m_s')]:
        if key in c:
            if c[key] <= 0:
                raise ValueError(key + ' must be positive m/s')
            rule(metric, 'gte', c[key], 'm/s')
    for key in ['target_contact', 'support_released']:
        if key in c:
            if c[key] is not True:
                raise ValueError(key + ' must be true')
            rule(key, 'eq', True, 'boolean')
    if 'heading_change_min_deg' in c:
        if not 0 < c['heading_change_min_deg'] <= 180:
            raise ValueError('heading change must be in (0, 180] degrees')
        rule('heading_change_deg', 'gte', c['heading_change_min_deg'], 'degrees')
    if 'surface_clearance_m' in c:
        clearance = c['surface_clearance_m']
        if not 0 < clearance['min'] <= clearance['max']:
            raise ValueError('surface clearance must be a positive ordered range in metres')
        rule('minimum_surface_clearance_m', 'gte', clearance['min'], 'm')
        rule('minimum_surface_clearance_m', 'lte', clearance['max'], 'm')
        rule('contact_in_window', 'eq', False, 'boolean')
        rule('bracketed_approach_and_separation', 'eq', True, 'boolean')
    if 'speed_max_m_s' in c:
        if c['speed_max_m_s'] < 0 or c['supported_duration_min_s'] <= 0:
            raise ValueError('catch requires nonnegative speed and positive supported duration')
        rule('terminal_speed_m_s', 'lte', c['speed_max_m_s'], 'm/s')
        rule('continuous_supported_duration_s', 'gte', c['supported_duration_min_s'], 's')
    return rules


def compile_failures(event, success):
    failures = []
    inverse = {'gte': 'lt', 'lte': 'gt', 'eq': 'ne'}
    if 'success_condition_not_met' in event['failure_conditions']:
        failures.append({'any': [{**p, 'operator': inverse[p['operator']]} for p in success]})
    if 'missed_time_window' in event['failure_conditions']:
        failures.append({'metric': 'event_time_s', 'operator': 'outside_half_open', 'value': event['time_window'], 'unit': 's'})
    if 'unphysical_motion' in event['failure_conditions']:
        failures.append({'metric': 'independent_physical_validation', 'operator': 'ne', 'value': 'PASSED', 'unit': 'status'})
    for code, metric in [('wrong_target', 'wrong_target_contact'), ('unexpected_contact', 'unplanned_salient_contact')]:
        if code in event['failure_conditions']:
            failures.append({'metric': metric, 'operator': 'eq', 'value': True, 'unit': 'boolean'})
    return failures
