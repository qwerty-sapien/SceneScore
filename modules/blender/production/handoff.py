"""Versioned, unapproved motion/music supplement; canonical 0.1 is untouched.

CLI: python -m modules.blender.production.handoff CANDIDATE [--out DIRECTORY]
Writes handoff.json, features.jsonl and handoff_hashes.json. Input scene, role,
state and validation bytes are hashed; no audio is composed or retimed here.

Features use causal backward position differences. Angular velocity is WORLD
frame log(q_current * inverse(q_previous))/dt with quaternion sign continuity.
A half-turn is ambiguous; gaps/missing/invalid samples never fabricate a zero.
Markers are copied only from a PASSED exact-input physical report, with explicit
scope, referenced report records, uncertainty and post-observation confirmation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

VERSION = 'scene-music-handoff-1'
FEATURE_VERSION = 'scene-motion-features-1'
FIELDS = ('velocity_world_m_s', 'speed_m_s', 'acceleration_world_m_s2',
          'acceleration_m_s2', 'angular_velocity_world_rad_s', 'angular_speed_rad_s')


def _digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path):
    return json.loads(Path(path).read_text())


def _norm(values):
    return math.sqrt(sum(x*x for x in values))


def _vector(value, size):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        return None
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in value):
        return None
    return tuple(value)


def _quaternion(value):
    q = _vector(value, 4)
    if q is None or abs(_norm(q)-1) > 1e-4:
        return None
    length = _norm(q)
    return tuple(x/length for x in q)


def _angular(before, after, dt):
    dot = sum(x*y for x, y in zip(before, after))
    if abs(dot) <= 1e-8:
        return None, 'ambiguous_half_turn'
    if dot < 0:
        after = tuple(-x for x in after)
    ax, ay, az, aw = after
    bx, by, bz, bw = (-before[0], -before[1], -before[2], before[3])
    vector = (aw*bx+ax*bw+ay*bz-az*by,
              aw*by-ax*bz+ay*bw+az*bx,
              aw*bz+ax*by-ay*bx+az*bw)
    scalar = aw*bw-ax*bx-ay*by-az*bz
    sine = _norm(vector)
    if sine <= 1e-14:
        return [0., 0., 0.], None
    angle = 2*math.atan2(sine, max(0., scalar))
    return [x*angle/(sine*dt) for x in vector], None


def _state_problem(sample, oid, tick, hz):
    if sample is None:
        return 'sample_missing'
    time = sample.get('time_s')
    if not isinstance(time, (int, float)) or not math.isfinite(time) or abs(time-tick/hz) > 1e-9:
        return 'invalid_sample_clock'
    if not isinstance(sample.get('objects'), dict) or not isinstance(sample['objects'].get(oid), dict):
        return 'object_state_missing'
    return None


def generate_features(samples, object_ids, hz=240, duration_s=None):
    """Yield a complete tick grid; absent source rows become explicit null records.

    Every reported derivative is tied to an interval. Velocity and speed use the
    previous/current endpoints; acceleration uses three consecutive positions.
    Endpoint velocity is therefore an interval estimate, not an instantaneous
    velocity assertion. Shortest-arc angular estimates cannot detect >pi aliasing.
    """
    if not isinstance(hz, int) or hz <= 0:
        raise ValueError('positive integer physics Hz required')
    ids = list(object_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('nonempty unique object IDs required')
    indexed, last = {}, -1
    for sample in samples:
        tick = sample.get('tick')
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0 or tick <= last:
            raise ValueError('source ticks must be unique, increasing nonnegative integers')
        indexed[tick], last = sample, tick
    count = last if duration_s is None else round(duration_s*hz)
    if count < 0 or count > 2_000_000 or last > count:
        raise ValueError('source tick range exceeds authoritative duration or work bound')
    if duration_s is not None and (not math.isfinite(duration_s) or abs(count-duration_s*hz) > 1e-8):
        raise ValueError('duration must align with the physics clock')
    previous_velocity = {oid: None for oid in ids}
    for tick in range(count+1):
        sample, previous = indexed.get(tick), indexed.get(tick-1)
        objects = {}
        for oid in ids:
            feature = {field: None for field in FIELDS}
            reasons = {field: None for field in FIELDS}
            problem = _state_problem(sample, oid, tick, hz)
            prior_problem = _state_problem(previous, oid, tick-1, hz) if tick else 'initial_sample'
            current_velocity = None
            interval = None
            acceleration_interval = None
            if problem or prior_problem:
                reason = problem or ('initial_sample' if tick == 0 else 'previous_'+prior_problem)
                reasons = dict.fromkeys(FIELDS, reason)
                if problem is None:
                    current = sample['objects'][oid]
                    if _vector(current.get('position_m'), 3) is None:
                        for field in FIELDS[:4]:
                            reasons[field] = 'position_missing_or_invalid'
                    if _quaternion(current.get('quaternion_xyzw')) is None:
                        for field in FIELDS[4:]:
                            reasons[field] = 'quaternion_missing_or_invalid'
            else:
                state, prior = sample['objects'][oid], previous['objects'][oid]
                position = _vector(state.get('position_m'), 3)
                before_position = _vector(prior.get('position_m'), 3)
                interval = [(tick-1)/hz, tick/hz]
                if position is None or before_position is None:
                    reason = 'position_missing_or_invalid' if position is None else 'previous_position_missing_or_invalid'
                    for field in FIELDS[:4]:
                        reasons[field] = reason
                else:
                    current_velocity = [(x-y)*hz for x, y in zip(position, before_position)]
                    feature['velocity_world_m_s'] = current_velocity
                    feature['speed_m_s'] = _norm(current_velocity)
                    old_velocity = previous_velocity[oid]
                    if old_velocity is None:
                        reasons['acceleration_world_m_s2'] = reasons['acceleration_m_s2'] = 'insufficient_valid_position_history'
                    else:
                        acceleration = [(x-y)*hz for x, y in zip(current_velocity, old_velocity)]
                        feature['acceleration_world_m_s2'] = acceleration
                        feature['acceleration_m_s2'] = _norm(acceleration)
                        acceleration_interval = [(tick-2)/hz, tick/hz]
                q, before_q = _quaternion(state.get('quaternion_xyzw')), _quaternion(prior.get('quaternion_xyzw'))
                if q is None or before_q is None:
                    reason = 'quaternion_missing_or_invalid' if q is None else 'previous_quaternion_missing_or_invalid'
                    reasons['angular_velocity_world_rad_s'] = reasons['angular_speed_rad_s'] = reason
                else:
                    angular, reason = _angular(before_q, q, 1/hz)
                    feature['angular_velocity_world_rad_s'] = angular
                    feature['angular_speed_rad_s'] = _norm(angular) if angular is not None else None
                    reasons['angular_velocity_world_rad_s'] = reasons['angular_speed_rad_s'] = reason
            feature.update(reasons=reasons, derivative_interval_s=interval,
                           acceleration_interval_s=acceleration_interval)
            previous_velocity[oid] = current_velocity
            objects[oid] = feature
        yield {'tick': tick, 'time_s': tick/hz, 'objects': objects}


def _inside(root, relative):
    path = (root/relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('referenced evidence missing or outside candidate: '+relative)
    return path


def _validation(root, inputs):
    path = root/'physical-validation.json'
    if not path.is_file():
        return None, {'status': 'NOT_RUN', 'reasons': ['physical-validation.json missing']}
    report_bytes = path.read_bytes()
    report = json.loads(report_bytes)
    problems = []
    if report.get('status') != 'PASSED':
        problems.append('physical report status is '+str(report.get('status', 'unknown')))
    for gate in ('asset_integrity', 'geometric_contact', 'physical_motion'):
        if report.get('gates', {}).get(gate, {}).get('status') != 'PASSED':
            problems.append(gate+' is not PASSED')
    checked = report.get('inputs', {})
    for name in ('production.json', 'physics_states.jsonl'):
        if checked.get(name) != inputs[name]:
            problems.append('missing or stale validation input: '+name)
    for name, expected in checked.items():
        try:
            if _digest(_inside(root, name)) != expected:
                problems.append('stale validation evidence: '+name)
        except (OSError, ValueError):
            problems.append('validation evidence missing or outside candidate: '+name)
    return report, {'status': 'PASSED' if not problems else 'UNVERIFIED', 'reasons': problems,
                    'report': {'path': path.name, 'sha256': hashlib.sha256(report_bytes).hexdigest()},
                    'reported_status': report.get('status')}


def _markers(root, production, inputs, report, validation):
    markers, unavailable = [], []
    if validation['status'] != 'PASSED':
        return markers, ['No validated markers: physical evidence is unavailable, incomplete or stale.']
    hz, duration = production['physics_hz'], production['duration_s']
    report_hash = validation['report']['sha256']
    ids = {obj['object_id'] for obj in production['objects']}
    dynamic_ids = {obj['object_id'] for obj in production['objects'] if obj['mode'] == 'dynamic'}

    def emit(kind, when, confirm, object_ids, report_pointer, source_path, source_pointer,
             *, spatial=None, scope, semantics=None):
        if (not isinstance(when, (int, float)) or not isinstance(confirm, (int, float))
                or not math.isfinite(when) or not math.isfinite(confirm)
                or not 0 <= when < duration or not when <= confirm <= duration
                or not object_ids or any(oid not in ids for oid in object_ids)):
            unavailable.append('Invalid bounded marker evidence at '+report_pointer)
            return
        first = max(0, math.floor(when*hz)-1)
        last = min(round(duration*hz), math.ceil(confirm*hz)+1)
        markers.append({'id': f'{kind}:{len(markers)}', 'type': kind, 'time_s': when,
            'confirmation_time_s': confirm, 'uncertainty_s': 1/hz, 'uncertainty_m': spatial,
            'uncertainty_m_reason': None if spatial is not None else 'not supplied by cited evidence',
            'object_ids': list(object_ids), 'status': 'VALIDATED', 'validation_scope': scope,
            'time_semantics': semantics or 'declared event time checked against stored samples',
            'physical_impulse_claim': False,
            'evidence': [{'path': 'physical-validation.json', 'sha256': report_hash, 'json_pointer': report_pointer},
                         {'path': source_path, 'sha256': inputs[source_path], 'json_pointer': source_pointer},
                         {'path': 'physics_states.jsonl', 'sha256': inputs['physics_states.jsonl'],
                          'tick_interval': [first, last]}]})

    cases = production.get('validation_cases', [])
    reported = report.get('metrics', {}).get('cases', [])
    for index, case in enumerate(cases):
        if index >= len(reported):
            unavailable.append('No corresponding case report at index '+str(index))
            continue
        result = reported[index]
        if result.get('kind') != case.get('kind') or result.get('id') != case.get('id') or result.get('status') != 'PASSED':
            if case.get('kind') in ('release', 'near_miss', 'supported_rest'):
                unavailable.append('Case not exactly matched and PASSED at index '+str(index))
            continue
        pointer = '/metrics/cases/'+str(index)
        end = case.get('end_s', duration)
        kind = case.get('kind')
        if kind == 'release':
            time = case.get('release_time_s')
            emit('release', time, max(end, min(duration, time+1/hz)) if isinstance(time, (int, float)) else end,
                 [case.get('object_id')], pointer, 'production.json', '/validation_cases/'+str(index),
                 scope='declared release velocity continuity case')
        elif kind == 'near_miss':
            metrics = result.get('metrics', {})
            time, gap, uncertainty = metrics.get('time_s'), metrics.get('minimum_sampled_gap_m'), metrics.get('uncertainty_m')
            if (not isinstance(time, (int, float)) or not case.get('start_s', 0) < time < end
                    or not isinstance(gap, (int, float)) or not isinstance(uncertainty, (int, float)) or gap <= uncertainty):
                unavailable.append('Near-miss report lacks an interior positive-gap minimum at index '+str(index))
                continue
            emit('near_miss', time, end, case.get('object_ids'), pointer, 'production.json',
                 '/validation_cases/'+str(index), spatial=uncertainty,
                 scope='sampled positive-clearance case; no global continuous-time guarantee')
        elif kind == 'supported_rest':
            if case.get('object_id') not in dynamic_ids:
                unavailable.append('Nondynamic supported-rest case is a state, not a settling event: '+str(case.get('object_id')))
                continue
            emit('settling', case.get('start_s', 0), end, [case.get('object_id')], pointer,
                 'production.json', '/validation_cases/'+str(index), scope='supported-rest case window',
                 semantics='start of verified rest window, not inferred first settling time')

    # The native validator checks event geometry only, and must seal the exact
    # event file in report.inputs before those declarations can be promoted.
    event_path = root/'production_events.json'
    if event_path.is_file():
        event_bytes = event_path.read_bytes()
        source = json.loads(event_bytes)
        inputs['production_events.json'] = hashlib.sha256(event_bytes).hexdigest()
        events = source.get('events', []) if isinstance(source, dict) else source
        evidence = report.get('metrics', {}).get('event_validation', {})
        checked_count = sum(event.get('type', event.get('event_type')) in ('contact', 'impact', 'near_miss', 'foley') for event in events)
        bound = report.get('inputs', {}).get('production_events.json') == inputs['production_events.json']
        if not bound or evidence.get('status') != 'CHECKED' or evidence.get('events_checked') != checked_count:
            unavailable.append('Contact declarations lack an exact event-file hash and matching geometry-check count')
        else:
            for index, event in enumerate(events):
                if event.get('type', event.get('event_type')) not in ('contact', 'impact'):
                    continue
                time = event.get('time_s', event.get('onset_s'))
                confirm = min(duration, (math.ceil(time*hz)+1)/hz) if isinstance(time, (int, float)) else time
                emit('contact', time, confirm, event.get('object_ids', event.get('pair')),
                     '/metrics/event_validation', 'production_events.json',
                     ('/events/' if isinstance(source, dict) else '/')+str(index),
                     scope='geometry-only declared contact; physical impact/impulse not certified')

    existing_rest = {oid for m in markers if m['type'] == 'settling' for oid in m['object_ids']}
    policy = report.get('tolerance_policy', {})
    for oid, rest in report.get('metrics', {}).get('rest', {}).items():
        window = rest.get('window_s')
        if oid not in dynamic_ids or oid in existing_rest or not isinstance(window, list) or len(window) != 2:
            continue
        speed_limit, angular_limit = policy.get('rest_speed_m_s'), policy.get('rest_angular_speed_rad_s')
        if (not rest.get('supported_at_end') or not isinstance(speed_limit, (int, float))
                or not isinstance(angular_limit, (int, float))
                or rest.get('max_final_speed_m_s', math.inf) > speed_limit
                or rest.get('max_final_angular_speed_rad_s', math.inf) > angular_limit):
            continue
        escaped = oid.replace('~', '~0').replace('/', '~1')
        emit('settling', window[0], window[1], [oid], '/metrics/rest/'+escaped,
             'production.json', '/objects/'+str(next(i for i, obj in enumerate(production['objects']) if obj['object_id'] == oid)),
             scope='reported final rest window; support checked at endpoint',
             semantics='start of low-motion final window, not independently localized first settling time')
    return sorted(markers, key=lambda item: (item['time_s'], item['id'])), unavailable


def _interval_markers(root, production, inputs, validation):
    """Import only exact persisted certificates reproduced by the independent helper."""
    from .export import verify_interval_report
    path = root/'contact_intervals.json'
    if not path.is_file():
        return [], [], {'status': 'NOT_RUN', 'reason': 'contact_intervals.json absent'}
    content = path.read_bytes()
    inputs[path.name] = hashlib.sha256(content).hexdigest()
    provenance = {'path': path.name, 'sha256': inputs[path.name], 'status': 'UNVERIFIED'}
    if validation['status'] != 'PASSED':
        return [], ['Interval contacts require a matching passed physical-validation report'], provenance
    try:
        report = verify_interval_report(root, json.loads(content))
        for name, expected in report['source_hashes'].items():
            if name in inputs and inputs[name] != expected:
                raise ValueError('interval evidence differs from already captured source: '+name)
            inputs[name] = expected
        provenance.update(status='PASSED', implementation_sha256=report['implementation_sha256'],
                          physical_evidence=report['physical_evidence'], coverage=report['coverage'])
        markers = []
        certificates = [('contacts', i, c) for i, c in enumerate(report['contacts'])]
        certificates += [('releases', i, c) for i, c in enumerate(report.get('releases', []))]
        for group, index, certificate in certificates:
            release = group == 'releases'
            if not 0 <= certificate['physical_time_estimate_s'] < production['duration_s']:
                continue
            markers.append({'id': ('interval-release:' if release else 'interval-contact:')+certificate['id'],
                'type': 'release' if release else 'contact',
                'time_s': certificate['physical_time_estimate_s'],
                'confirmation_time_s': certificate['confirmation_time_s'],
                'uncertainty_s': certificate['time_uncertainty_s'],
                'uncertainty_m': report['policy']['contact_continuity_m'], 'uncertainty_m_reason': None,
                'object_ids': certificate['object_ids'], 'status': 'VALIDATED',
                'validation_scope': (certificate['checked']+'; '+certificate['not_checked'] if release else
                                     'independent ballistic contact-free fits and normal restitution response; partial contact coverage'),
                'time_semantics': ('fitted support departure between evaluated ticks' if release else
                                   'fitted physical contact between evaluated ticks, not a sampled-touch declaration'),
                'physical_impulse_claim': False, 'incoming_normal_m_s': certificate.get('incoming_normal_m_s'),
                'outgoing_normal_m_s': certificate.get('outgoing_normal_m_s'),
                'fit_pair_sha256': certificate['fit_pair_sha256'],
                'evidence': [{'path': path.name, 'sha256': inputs[path.name], 'json_pointer': '/'+group+'/'+str(index)},
                             {'path': 'physics_states.jsonl', 'sha256': inputs['physics_states.jsonl'],
                              'tick_interval': [certificate['pre_support_fit' if release else 'pre_fit']['ticks'][0],
                                                certificate['post_flight_fit' if release else 'post_fit']['ticks'][-1]]},
                             {'path': 'physical-validation.json', 'sha256': inputs['physical-validation.json']},
                             {'path': 'solver_calibration.json', 'sha256': inputs['solver_calibration.json']}]})
        return markers, [], provenance
    except (OSError, ValueError, KeyError, TypeError) as error:
        provenance['reason'] = str(error)
        return [], ['Interval certificates unavailable or stale: '+str(error)], provenance


def build_handoff(candidate, output=None):
    """Write standalone files; return the handoff payload and persisted-byte index."""
    root = Path(candidate).resolve()
    destination = Path(output).resolve() if output else root
    metadata_bytes = {name: (root/name).read_bytes() for name in
                      ('production.json', 'manifest.json', 'object_roles.json', 'physics_states.jsonl')}
    production, manifest, roles = (json.loads(metadata_bytes[name]) for name in
                                  ('production.json', 'manifest.json', 'object_roles.json'))
    hz, fps, duration = production['physics_hz'], production['render_fps'], production['duration_s']
    if fps != 30 or not isinstance(hz, int) or hz <= 0 or hz % 30 or not math.isfinite(duration) or duration <= 0:
        raise ValueError('authoritative clock requires native 30 fps and integral physics ticks per frame')
    frame_count = round(duration*30)
    if abs(frame_count-duration*30) > 1e-8:
        raise ValueError('animation duration must contain an integral video frame count')
    if (manifest.get('fps') != 30 or manifest.get('fps_base') != 1
            or manifest.get('duration_s') != duration or roles.get('scene_id') != manifest.get('id')):
        raise ValueError('export scene/role identity or authoritative clock mismatch')
    spec_ids = [obj['object_id'] for obj in production['objects']]
    expected_roles = [{key: obj[key] for key in ('object_id', 'sonic_identity_id', 'role', 'scored', 'mode')}
                      for obj in production['objects']]
    if (roles.get('roles_version') != 'blender-object-roles-1' or roles.get('objects') != expected_roles
            or roles.get('scored_object_ids') != [o['object_id'] for o in expected_roles if o['scored']]):
        raise ValueError('exported roles differ from production object/scoring semantics')
    source = _inside(root, 'scene.blend')
    if manifest.get('source_hash') != _digest(source):
        raise ValueError('scene source bytes differ from exported manifest')
    names = ('production.json', 'manifest.json', 'object_roles.json', 'physics_states.jsonl', 'scene.blend')
    inputs = {name: hashlib.sha256(metadata_bytes[name]).hexdigest() if name in metadata_bytes
              else _digest(_inside(root, name)) for name in names}
    samples = [json.loads(line) for line in metadata_bytes['physics_states.jsonl'].splitlines() if line.strip()]
    report, validation = _validation(root, inputs)
    markers, unavailable = _markers(root, production, inputs, report, validation)
    interval_markers, interval_unavailable, interval_provenance = _interval_markers(root, production, inputs, validation)
    for interval in interval_markers:
        markers = [marker for marker in markers if not (marker['type'] == interval['type']
                   and (sorted(marker['object_ids']) == sorted(interval['object_ids'])
                        or (interval['type'] == 'release' and set(marker['object_ids']) <= set(interval['object_ids'])))
                   and abs(marker['time_s']-interval['time_s']) <= 1/hz+1e-12)]
        markers.append(interval)
    markers.sort(key=lambda marker: (marker['time_s'], marker['id']))
    unavailable.extend(interval_unavailable)
    features = list(generate_features(samples, spec_ids, hz, duration))
    bad_source = len(samples) != round(duration*hz)+1
    bad_source |= any(_state_problem(row, oid, row['tick'], hz)
                      or _vector(row.get('objects', {}).get(oid, {}).get('position_m'), 3) is None
                      or _quaternion(row.get('objects', {}).get(oid, {}).get('quaternion_xyzw')) is None
                      for row in samples for oid in spec_ids)
    if bad_source or any(feature['reasons']['speed_m_s'] not in (None, 'initial_sample')
                         for row in features for feature in row['objects'].values()):
        markers = []
        unavailable.append('Source-state gaps or invalid positions prevent marker promotion')
        validation = {**validation, 'status': 'UNVERIFIED',
                      'reasons': [*validation['reasons'], 'source-state coverage is incomplete or invalid']}
    feature_bytes = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n'
                            for row in features).encode()
    if (root/'physical-validation.json').is_file():
        inputs['physical-validation.json'] = validation['report']['sha256']
    if (root/'production_events.json').is_file():
        inputs.setdefault('production_events.json', _digest(root/'production_events.json'))
    payload = {'handoff_version': VERSION, 'scene_id': manifest['id'], 'approval': None,
        'generator': {'version': VERSION, 'source_sha256': _digest(Path(__file__))},
        'source_bundle': {'path': str(root), 'scene_id': manifest['id']},
        'source_mode': production.get('source_mode', 'synthetic'), 'adaptive_scoring_status': 'PENDING_SEPARATE_DAG',
        'clock': {'duration_s': duration, 'render_interval': '[0,duration_s)', 'audit_includes_right_endpoint': True,
                  'video_fps': 30, 'video_start_frame': 1, 'video_frame_count': frame_count,
                  'physics_hz': hz, 'physics_ticks_per_video_frame': hz//30,
                  'physics_tick_count_including_endpoint': round(duration*hz)+1,
                  'audio_sample_rate_hz': 48000, 'audio_samples_per_video_frame': 1600,
                  'audio_sample_count': frame_count*1600,
                  'render_verification': 'frame count derived from source clock; decoded media validation is a separate gate',
                  'mapping': 'scene_time=tick/physics_hz; Blender_frame=1+scene_time*30; audio_sample=scene_time*48000'},
        'source_fingerprint': production.get('source_fingerprint'), 'input_hashes': inputs,
        'role_hash': inputs['object_roles.json'], 'objects': expected_roles,
        'features': {'version': FEATURE_VERSION, 'path': 'features.jsonl', 'sha256': hashlib.sha256(feature_bytes).hexdigest(),
                     'row_count': len(features), 'derivative_method': 'causal backward finite differences; acceleration needs three contiguous positions',
                     'angular_method': 'world quaternion delta q_current * inverse(q_previous), sign-continuous shortest arc',
                     'angular_limitations': 'a half-turn is ambiguous and null; rotations over pi per sample are unobservable aliases',
                     'units': {'speed': 'm/s', 'acceleration': 'm/s^2', 'angular_velocity': 'world rad/s'},
                     'missing_policy': 'null with a per-field reason; no interpolation across missing samples'},
        'interval_contact_provenance': interval_provenance,
        'marker_validation': validation, 'markers': markers, 'unavailable_markers': unavailable,
        'limitations': ['Motion derivatives across contact are interval estimates, not smooth instantaneous forces.',
                        'Validated geometry markers do not imply a measured impulse, auditory judgment or human approval.',
                        'No adaptive music, score retiming, Muse or EEG processing is performed.']}
    if any(_digest(root/name) != expected for name, expected in inputs.items()):
        raise RuntimeError('source evidence changed during handoff generation')
    handoff_bytes = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    index = {'hash_version': 'sha256-persisted-bytes-1', 'files': {
        'handoff.json': hashlib.sha256(handoff_bytes).hexdigest(), 'features.jsonl': hashlib.sha256(feature_bytes).hexdigest()}}
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in [('features.jsonl', feature_bytes), ('handoff.json', handoff_bytes),
                       ('handoff_hashes.json', (json.dumps(index, sort_keys=True, indent=2)+'\n').encode())]:
        temporary = destination/(name+'.tmp')
        temporary.write_bytes(data)
        temporary.replace(destination/name)
    return payload, index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    payload, index = build_handoff(args.candidate, args.out)
    print(json.dumps({'status': 'EXPORTED_UNAPPROVED', 'marker_validation': payload['marker_validation']['status'],
                      'markers': len(payload['markers']), 'files': index['files']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
