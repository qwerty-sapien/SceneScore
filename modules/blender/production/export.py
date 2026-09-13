"""Canonical 0.1 views of finalized evaluated production motion; never runs Blender.

Contact is a geometric observation, not a force or an independent physics pass.
The versioned roles/geometry supplements keep that distinction outside contract 0.1.
"""
import itertools
import json
import math
from pathlib import Path
import shutil

from modules.blender.geometry import area
from . import validation as independent_validation
from . import contact_intervals
from .common import data_hash, digest, dump, read, rows
from .validation import VERSION as VALIDATOR_VERSION, angular_distance, gap, tolerance, validate_candidate

VERSION = 'blender-production-export-1'


def _norm(v):
    return math.sqrt(sum(x*x for x in v))


def _difference(a, b):
    return [x-y for x, y in zip(a, b)]


def _transform(pose):
    q = pose['quaternion_xyzw']
    length = _norm(q)
    if length < 1e-12 or abs(length-1) > 1e-5:
        raise ValueError('invalid evaluated quaternion')
    x, y, z, w = [v/length for v in q]
    sx, sy, sz = pose['scale']
    p = pose['position_m']
    matrix = [(1-2*(y*y+z*z))*sx, 2*(x*y-z*w)*sy, 2*(x*z+y*w)*sz, p[0],
              2*(x*y+z*w)*sx, (1-2*(x*x+z*z))*sy, 2*(y*z-x*w)*sz, p[1],
              2*(x*z-y*w)*sx, 2*(y*z+x*w)*sy, (1-2*(x*x+y*y))*sz, p[2],
              0, 0, 0, 1]
    return {'position_m': list(p), 'quaternion_xyzw': [x, y, z, w], 'matrix_row_major': matrix}


def _world_vertices(geometry, transform):
    m = transform['matrix_row_major']
    return [[sum(m[4*i+j]*v[j] for j in range(3))+m[4*i+3] for i in range(3)]
            for v in geometry['vertices_local']]


def _travel_bound(spec, before, after):
    """Surface travel bound for translation plus shortest sampled rotation."""
    scale = before['scale']
    radius = (spec['radius_m']*abs(scale[0]) if spec['shape'] == 'sphere'
              else _norm([h*s for h, s in zip(spec['half_extents_m'], scale)]))
    return (math.dist(before['position_m'], after['position_m'])
            + radius*angular_distance(before['quaternion_xyzw'], after['quaternion_xyzw']))


def _pair_observations(a, b, samples):
    aid, bid = a['object_id'], b['object_id']
    margins = [s.get('collision_margin_m', 0.) for s in (a, b)]
    if any(not math.isfinite(m) or m < 0 for m in margins):
        raise ValueError('collision margins must be finite nonnegative metres')
    observations = []
    for i, sample in enumerate(samples):
        sa, sb = sample['objects'][aid], sample['objects'][bid]
        measured = gap(a, sa, b, sb)
        allowed = min(tolerance(a, sa), tolerance(b, sb))
        distance = math.dist(sa['position_m'], sb['position_m'])
        normal_speed, tangent_speed = None, None
        travel = 0.
        if i:
            previous = samples[i-1]
            pa, pb = previous['objects'][aid], previous['objects'][bid]
            dt = sample['time_s']-previous['time_s']
            # Gap derivative follows the surface separation, not the centre radial
            # direction (which is wrong for offset box-face contact).
            normal_speed = (measured-observations[-1]['gap'])/dt
            relative = [v/dt for v in _difference(_difference(sb['position_m'], sa['position_m']),
                                                 _difference(pb['position_m'], pa['position_m']))]
            # The canonical field is a centre-motion tangent estimate; rotations
            # and contact-point tangents are explicitly not measured here.
            delta = _difference(sb['position_m'], sa['position_m'])
            radial = sum(v*d for v, d in zip(relative, delta))/distance if distance else 0.
            tangent_speed = math.sqrt(max(0., _norm(relative)**2-radial**2))
            travel = _travel_bound(a, pa, sa)+_travel_bound(b, pb, sb)
        observations.append({'t': sample['time_s'], 'gap': measured, 'tolerance': allowed,
                             'contact_envelope': allowed+sum(margins),
                             'distance': distance, 'normal': normal_speed,
                             'tangent': tangent_speed, 'travel_bound': travel})
    return observations


def _validation_status(out, inputs):
    """A status label alone cannot certify events from new or changed bytes."""
    evidence = {'validated': False, 'scope': 'candidate physics; no impulse or perceptual certification',
                'report': 'physical-validation.json', 'reason': 'matching passed validator report unavailable'}
    path = out/'physical-validation.json'
    if not path.is_file():
        return evidence
    report = read(path)
    wanted = {name: inputs[name] for name in ('production.json', 'physics_states.jsonl')}
    gates = ('asset_integrity', 'geometric_contact', 'physical_motion', 'fresh_process_replay', 'solver_calibration')
    matching = (report.get('version') == VALIDATOR_VERSION and report.get('status') == 'PASSED'
                and report.get('candidate') == str(out)
                and all(report.get('inputs',{}).get(name)==value for name,value in wanted.items())
                and not report.get('issues')
                and all(report.get('gates', {}).get(g, {}).get('status') == 'PASSED' for g in gates))
    if matching:
        # Recompute independently instead of trusting a copied "PASSED" string.
        evidence['report_sha256'] = digest(path)
        current = validate_candidate(out)
        matching = current.get('status') == 'PASSED' and current.get('inputs') == report.get('inputs')
        evidence['recomputed_status'] = current.get('status')
    if matching:
        evidence.update(validated=True, reason=None, validator_version=VALIDATOR_VERSION,
                        validator_sha256=digest(Path(independent_validation.__file__)),
                        inputs=wanted)
    return evidence


def verify_interval_report(out, report, *, recompute=True):
    """Require exact current proofs, not a copied certificate's status flags."""
    out = Path(out).resolve()
    if (report.get('version') != contact_intervals.VERSION or report.get('backend') != contact_intervals.BACKEND
            or report.get('status') != 'PASSED' or report.get('coverage', {}).get('complete') is not False
            or report.get('implementation_sha256') != digest(Path(contact_intervals.__file__))):
        raise ValueError('interval certificate version, implementation, coverage or status is unverified')
    sources = report.get('source_hashes', {})
    if not {'production.json', 'physics_states.jsonl', 'solver_calibration.json', 'replay_validation.json'} <= sources.keys():
        raise ValueError('interval certificate lacks source/calibration/replay hash bindings')
    for name, expected in sources.items():
        path = (out/name).resolve()
        if not path.is_relative_to(out) or not path.is_file() or digest(path) != expected:
            raise ValueError('stale interval certificate source: '+name)
    evidence = report.get('physical_evidence', {})
    required = ('asset_integrity', 'geometric_contact', 'physical_motion', 'fresh_process_replay', 'solver_calibration')
    if (evidence.get('recomputed_status') != 'PASSED' or evidence.get('eligible') is not True
            or evidence.get('issues') != []
            or any(evidence.get('gates', {}).get(g, {}).get('status') != 'PASSED' for g in required)):
        raise ValueError('interval certificate lacks overall independent physical pass')
    production = read(out/'production.json')
    ids = {obj['object_id'] for obj in production['objects']}
    hz, duration = production['physics_hz'], production['duration_s']
    seen = set()
    for certificate in [*report.get('contacts', []), *report.get('releases', [])]:
        release = certificate.get('kind') == 'supported_release'
        pair, tick = certificate.get('object_ids', []), certificate.get('tick_interval', [])
        time, uncertainty, confirmation = (certificate.get(key) for key in
            ('physical_time_estimate_s', 'time_uncertainty_s', 'confirmation_time_s'))
        expected_fit = data_hash({'pre': certificate.get('pre_support_fit' if release else 'pre_fit'),
                                  'post': certificate.get('post_flight_fit' if release else 'post_fit'),
                                  'pair': pair, 'time_s': time})
        if (certificate.get('numerical_status') != 'PASSED' or certificate.get('validated') is not True
                or len(pair) != 2 or len(set(pair)) != 2 or any(oid not in ids for oid in pair)
                or certificate.get('sphere_id') not in pair or certificate.get('support_id' if release else 'obstacle_id') not in pair
                or certificate.get('id') in seen or not certificate.get('id')
                or certificate.get('fit_pair_sha256') != expected_fit
                or certificate.get('source_hashes') != {name: sources[name] for name in ('production.json', 'physics_states.jsonl')}
                or len(tick) != 2 or any(not isinstance(t, int) for t in tick) or tick[1] != tick[0]+1
                or not all(isinstance(t, (int, float)) and math.isfinite(t) for t in (time, uncertainty, confirmation))
                or not 0 <= tick[0]/hz <= time <= tick[1]/hz <= duration
                or not time <= confirmation <= duration or not math.isclose(uncertainty, 1/hz, abs_tol=1e-10)):
            raise ValueError('invalid or unbound individual interval certificate')
        seen.add(certificate['id'])
    if recompute and data_hash(contact_intervals.certify_candidate(out)) != data_hash(report):
        raise ValueError('interval certificate differs from independent current recomputation')
    return report


def _merge_interval_events(events, details, interval_report, samples, specs, scene_id, record, inputs, validation):
    """Prefer one certified physical onset over a neighbouring sampled onset."""
    if interval_report is None:
        return events, details
    by_id = {spec['object_id']: spec for spec in specs}
    duration, hz = samples[-1]['time_s'], 1/(samples[1]['time_s']-samples[0]['time_s'])
    certificates = [('contacts', i, c) for i, c in enumerate(interval_report['contacts'])]
    certificates += [('releases', i, c) for i, c in enumerate(interval_report.get('releases', []))]
    for group, index, certificate in certificates:
        release = group == 'releases'
        event_type = 'contact_release' if release else 'contact_onset'
        when, pair = certificate['physical_time_estimate_s'], sorted(certificate['object_ids'])
        if not 0 <= when < duration:
            continue
        matched = next((e for e in events if e['event_type'] == event_type and sorted(e['pair']) == pair
                        and abs(e['onset_s']-when) <= 1/hz+1e-12), None)
        pair_id = '|'.join(pair)
        eid = matched['id'] if matched else f'{scene_id}:{pair_id}:{certificate["id"]}'
        sphere_id = certificate['sphere_id']
        obstacle_id = certificate['support_id' if release else 'obstacle_id']
        position = (contact_intervals.evaluate_fit(certificate['post_flight_fit'], when)[0] if release
                    else certificate['position_at_contact_m'])
        sphere_pose = dict(samples[0]['objects'][sphere_id], position_m=position)
        obstacle_pose = samples[0]['objects'][obstacle_id]
        fitted_gap = gap(by_id[sphere_id], sphere_pose, by_id[obstacle_id], obstacle_pose)
        spatial = interval_report['policy']['contact_continuity_m']
        # Contract 0.1 requires numeric kinematics. Keep the measured, causal
        # neighbouring-sample centre tangent; do not invent an unmeasured impulse.
        kinematic_index = min(len(samples)-1, max(1, math.ceil(when*hz)))
        motion = _pair_observations(by_id[sphere_id], by_id[obstacle_id], samples)[kinematic_index]
        event = record('InteractionEvent', eid, scene_id=scene_id, pair=pair, pair_id=pair_id,
                       loop_instance=0, event_type=event_type, onset_s=when, duration_s=0.,
                       centre_distance_m=math.dist(position, obstacle_pose['position_m']),
                       surface_gap_m=fitted_gap, relative_normal_speed_m_s=motion['normal'] if release else certificate['incoming_normal_m_s'],
                       relative_tangential_speed_m_s=motion['tangent'], method='baked', physical_impact=False,
                       impulse_ns=None, uncertainty_m=spatial)
        detail = {'id': eid, 'minimum_gap_time_s': when, 'end_s': when,
                  'confirmation_time_s': certificate['confirmation_time_s'],
                  'time_uncertainty_s': certificate['time_uncertainty_s'],
                  'geometry_method': ('independent_supported_release_between_ticks' if release
                                      else 'independent_ballistic_face_contact_between_ticks'),
                  'source': 'contact_intervals.json; independent fits of evaluated physics states',
                  'source_tick_interval': certificate['tick_interval'],
                  'signed_surface_gap_m': fitted_gap, 'gap_semantics': 'fitted position at departure' if release else 'fitted contact position, not sampled touch',
                  'physical_dynamics': interval_report['backend']+('; independently fitted supported departure' if release else '; independently fitted normal response only'),
                  'physics_backend': interval_report['backend'],
                  'validated': True, 'validation_evidence': validation, 'source_evidence': inputs.copy(),
                  'foley_eligible': not release,
                  'foley_ineligible_reason': 'supported release is not a contact onset' if release else None,
                  'kinematic_sample_tick': samples[kinematic_index]['tick'],
                  'normal_speed_method': 'causal signed-gap difference at neighbouring sample' if release else 'incoming ballistic fit projected onto obstacle outward normal',
                  'tangential_speed_method': 'causal centre tangent at neighbouring sample; no tangential-response certification',
                  'interval_certificate': {'path': 'contact_intervals.json', 'sha256': inputs['contact_intervals.json'],
                                           'json_pointer': '/'+group+'/'+str(index), 'id': certificate['id'],
                                           'fit_pair_sha256': certificate['fit_pair_sha256']},
                  'interval_evidence': certificate,
                  'coverage_complete': False, 'physical_impulse_claim': False}
        if matched:
            detail['deduplicated_sampled_event'] = {'onset_s': matched['onset_s'], 'surface_gap_m': matched['surface_gap_m']}
            events.remove(matched)
            details[:] = [d for d in details if d['id'] != matched['id']]
        events.append(event)
        details.append(detail)
    return sorted(events, key=lambda e: (e['onset_s'], e['id'])), details


def _events(specs, samples, scene_id, record, production, inputs, validation):
    events, details, pairs, unknown = [], [], [], []
    for a, b in itertools.combinations(specs, 2):
        if a['mode'] == b['mode'] == 'passive':
            continue
        if a.get('collision_group') and a.get('collision_group') == b.get('collision_group'):
            continue
        pair = sorted([a['object_id'], b['object_id']])
        pair_id = '|'.join(pair)
        observations = _pair_observations(a, b, samples)
        minimum = min(observations, key=lambda r: r['gap'])
        method = ('oriented_box_SAT_separation_bound' if a['shape'] == b['shape'] == 'box'
                  else 'analytic_sphere_or_oriented_box_signed_distance')
        pairs.append({'pair': pair, 'pair_id': pair_id, 'minimum_gap_m': minimum['gap'],
                      'minimum_gap_time_s': minimum['t'], 'method': method,
                      'penetration_tolerance_m': minimum['tolerance'],
                      'collision_margins_m': {s['object_id']: s.get('collision_margin_m', 0.) for s in (a, b)},
                      'contact_envelope_m': minimum['contact_envelope']})
        if not a.get('collision_enabled', True) or not b.get('collision_enabled', True):
            unknown.append({'pair_id': pair_id, 'reason': 'collider disabled; no physical contact event exported'})
            continue

        def emit(kind, at, uncertainty, end_index=None):
            sample = observations[at]
            eid = f'{scene_id}:{pair_id}:e{len(events)}'
            # Only onsets are canonical contact events: no sustain/release Foley
            # flood and no force/impulse inferred from proximity.
            event = record('InteractionEvent', eid, scene_id=scene_id, pair=pair, pair_id=pair_id,
                           loop_instance=0, event_type=kind, onset_s=sample['t'], duration_s=0.,
                           centre_distance_m=sample['distance'], surface_gap_m=sample['gap'],
                           relative_normal_speed_m_s=sample['normal'],
                           relative_tangential_speed_m_s=sample['tangent'], method='baked',
                           physical_impact=False, impulse_ns=None, uncertainty_m=uncertainty)
            events.append(event)
            end = end_index if end_index is not None else at
            details.append({'id': eid, 'minimum_gap_time_s': sample['t'], 'end_s': observations[end]['t'],
                            'confirmation_time_s': observations[end]['t'], 'geometry_method': method,
                            'source_tick': samples[at]['tick'],
                            'source': 'physics_states.jsonl; production collider dimensions',
                            'physical_dynamics': production['motion_mode']+'; impact response not certified by exporter',
                            'physics_backend': production.get('physics_backend', production.get('backend', production['motion_mode'])),
                            'signed_surface_gap_m': sample['gap'],
                            'penetration_tolerance_m': sample['tolerance'],
                            'collision_margins_m': {s['object_id']: s.get('collision_margin_m', 0.) for s in (a, b)},
                            'contact_envelope_m': sample['contact_envelope'],
                            'validated': validation['validated'], 'validation_evidence': validation,
                            'foley_eligible': False,
                            'foley_ineligible_reason': ('sampled contact envelope does not independently certify physical impact timing'
                                                        if kind == 'contact_onset' else 'not a certified contact onset'),
                            'time_semantics': 'sampled_envelope_entry' if kind == 'contact_onset' else 'sampled_positive_gap_minimum',
                            'physical_impact_time_s': None, 'physical_impact_time_uncertainty_s': None,
                            'physical_impact_time_reason': 'sampled geometry alone does not establish physical impact time',
                            'source_evidence': {name: inputs[name] for name in
                                                ('production.json', 'physics_states.jsonl', 'evaluated_geometry.json', 'scene.blend')},
                            'time_uncertainty_s': samples[1]['time_s']-samples[0]['time_s'],
                            'normal_speed_method': 'causal signed surface-gap difference',
                            'tangential_speed_method': 'causal centre motion orthogonal to centre line; excludes spin'})

        # Initial support is a state, not a new impact. Re-arm only after a clear
        # separation wider than the frozen tolerance; slight solver jitter cannot
        # create a contact onset on every frame.
        armed = observations[0]['gap'] > 2*observations[0]['contact_envelope']
        for i, obs in enumerate(observations[1:], 1):
            if obs['gap'] > 2*obs['contact_envelope']:
                armed = True
            elif armed and obs['gap'] <= obs['contact_envelope']:
                # Margins extend the positive contact envelope only. They never
                # excuse deeper interpenetration of the underlying solids.
                if obs['gap'] >= -obs['tolerance'] and obs['t'] < samples[-1]['time_s']:
                    emit('contact_onset', i, obs['contact_envelope'])
                else:
                    unknown.append({'pair_id': pair_id, 'time_s': obs['t'],
                                    'reason': 'contact crossed outside tolerance or beyond render interval'})
                armed = False

        # Conservative single closest-approach certificate. All sampled intervals
        # must stay clear under a translation/rotation surface-travel bound. This
        # is an explicit interpolation/sampling limit, not continuous observation.
        at = observations.index(minimum)
        if 0 < at < len(observations)-1 and minimum['gap'] > minimum['contact_envelope']:
            left = next((i for i in range(at-1, -1, -1)
                         if observations[i]['gap'] > minimum['gap']+minimum['tolerance']), None)
            right = next((i for i in range(at+1, len(observations))
                          if observations[i]['gap'] > minimum['gap']+minimum['tolerance']), None)
            bound = max(r['travel_bound']+r['contact_envelope'] for r in observations)
            certified = all(min(x['gap'], y['gap']) > y['travel_bound']+max(x['contact_envelope'], y['contact_envelope'])
                            for x, y in zip(observations, observations[1:]))
            if left is not None and right is not None and certified and minimum['gap'] > bound:
                emit('near_miss', at, bound, right)
            elif left is not None and right is not None:
                unknown.append({'pair_id': pair_id, 'time_s': minimum['t'],
                                'reason': 'positive sampled minimum lacks conservative inter-sample clearance'})
    return sorted(events, key=lambda e: (e['onset_s'], e['id'])), details, pairs, unknown


def export_bundle(out):
    """Write canonical records and sealed artifact index for one finalized candidate.

    Requires actual evaluated meshes and saved replay. Validation/render reports
    remain separate; exporting never promotes a candidate to an accepted status.
    """
    out = Path(out).resolve()
    production = read(out/'production.json')
    geometry = read(out/'evaluated_geometry.json')
    samples = list(rows(out/'physics_states.jsonl'))
    specs = production['objects']
    identifiers = {s['object_id'] for s in specs}
    hz, fps, duration = production['physics_hz'], production['render_fps'], production['duration_s']
    if len(identifiers) != len(specs) or not identifiers:
        raise ValueError('duplicate or empty physical body IDs')
    if hz <= 0 or fps <= 0 or hz % fps or not math.isclose(duration*fps, round(duration*fps), abs_tol=1e-8):
        raise ValueError('production clock is not aligned to native render frames')
    if len(samples) != round(duration*hz)+1:
        raise ValueError('physics states omit the complete audit interval')
    for i, sample in enumerate(samples):
        if sample['tick'] != i or not math.isclose(sample['time_s'], i/hz, abs_tol=1e-9):
            raise ValueError('non-native, missing or nonmonotonic physics tick')
        if set(sample['objects']) != identifiers:
            raise ValueError('physical object coverage mismatch')
        for oid, pose in sample['objects'].items():
            if any(abs(a-b) > 1e-5 for a, b in zip(pose['scale'], samples[0]['objects'][oid]['scale'])):
                raise ValueError('rigid scale changed; revalidation required')
    source_hash = digest(out/'scene.blend')
    input_files = ['production.json', 'evaluated_geometry.json', 'physics_states.jsonl', 'scene.blend']
    for name in ('simulation.blend', 'bake.json'):
        if (out/name).is_file():
            input_files.append(name)
    inputs = {name: digest(out/name) for name in input_files}
    validation = _validation_status(out, inputs)
    interval_report = None
    interval_reason = None
    if production.get('motion_mode') == contact_intervals.BACKEND:
        if validation['validated']:
            try:
                interval_report = verify_interval_report(out, contact_intervals.certify_candidate(out), recompute=False)
                dump(out/'contact_intervals.json', interval_report)
                for name in [*interval_report['source_hashes'], 'contact_intervals.json']:
                    if name not in input_files:
                        input_files.append(name)
                    inputs[name] = digest(out/name)
            except (OSError, ValueError, KeyError, TypeError) as error:
                interval_report = None
                interval_reason = 'interval certification unavailable: '+str(error)
        else:
            interval_reason = 'interval contacts require matching stored and independently recomputed overall physical pass'
    export_hash = digest(Path(__file__))
    identity = data_hash({'inputs': inputs, 'exporter': export_hash})
    scene_id = f'{production["recipe_id"]}:{production["variant"]}:{identity[:16]}'
    prov = {'source_mode': production['source_mode'], 'creator': VERSION,
            'tool_version': production['blender_version'], 'config_hash': identity,
            'input_hashes': [*inputs.values(), export_hash], 'seed': production['seed']}

    def record(kind, rid, **fields):
        return {'kind': kind, 'schema_version': '0.1', 'id': rid, 'provenance': prov, **fields}

    static, summaries = {}, {}
    selected = {0, len(samples)//4, len(samples)//2, 3*len(samples)//4, len(samples)-1}
    previous = {}
    with (out/'object_states.jsonl').open('w') as output:
        for i, sample in enumerate(samples):
            for spec in specs:
                oid = spec['object_id']
                pose = sample['objects'][oid]
                mesh = geometry[oid]
                if not mesh['vertices_local'] or not mesh['triangles']:
                    raise ValueError('actual evaluated mesh missing')
                transform = _transform(pose)
                vertices = _world_vertices(mesh, transform)
                if i == 0:
                    measured_area = area(vertices, mesh['triangles'])
                    if not math.isclose(measured_area, mesh['surface_area_m2'], rel_tol=1e-5, abs_tol=1e-8):
                        raise ValueError('evaluated mesh area does not match initial transformed vertices')
                    static[oid] = {'object_id': oid, 'sonic_identity_id': spec['sonic_identity_id'],
                                   'shape': spec['shape'], 'role': spec['role'], 'scale': pose['scale'],
                                   'material_rgba': mesh['material_rgba'], 'surface_area_m2': measured_area,
                                   'volume_m3': None, 'volume_reason': 'watertightness/orientation not certified',
                                   'geometry_method': mesh['method'], 'contact_proxy': spec['shape'],
                                   'proxy_note': 'physical sphere/OBB collider; display bevel/tessellation differs'}
                    summaries[oid] = {**static[oid], 'motion_envelope': {'min_m': pose['position_m'][:],
                                      'max_m': pose['position_m'][:], 'max_speed_m_s': 0.}, 'keyframes': []}
                velocity = [v*hz for v in _difference(pose['position_m'], previous[oid][0])] if i else None
                acceleration = ([v*hz for v in _difference(velocity, previous[oid][1])] if i >= 2 else None)
                previous[oid] = (pose['position_m'], velocity)
                state = record('ObjectState', f'{scene_id}:{oid}:s{i}', scene_id=scene_id, object_id=oid,
                               scene_time_s=sample['time_s'], frame=1+i*fps/hz, transform=transform,
                               velocity_m_s=velocity, acceleration_m_s2=acceleration,
                               derivative_method=f'causal backward difference dt={1/hz:.12g}s; contact windows not smooth',
                               bounds_min_m=[min(v[j] for v in vertices) for j in range(3)],
                               bounds_max_m=[max(v[j] for v in vertices) for j in range(3)],
                               surface_area_m2=static[oid]['surface_area_m2'], volume_m3=None,
                               unavailable_reason='volume not certified; initial velocity/acceleration need preceding samples')
                output.write(json.dumps(state, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summaries[oid]
                envelope = summary['motion_envelope']
                for axis in range(3):
                    envelope['min_m'][axis] = min(envelope['min_m'][axis], pose['position_m'][axis])
                    envelope['max_m'][axis] = max(envelope['max_m'][axis], pose['position_m'][axis])
                envelope['max_speed_m_s'] = max(envelope['max_speed_m_s'], _norm(velocity or [0, 0, 0]))
                if i in selected:
                    summary['keyframes'].append(state)
    events, details, pairs, unknown = _events(specs, samples, scene_id, record, production, inputs, validation)
    events, details = _merge_interval_events(events, details, interval_report, samples, specs, scene_id, record, inputs, validation)
    if interval_reason:
        unknown.append({'reason': interval_reason, 'source': 'contact_intervals.json'})
    (out/'interactions.jsonl').write_text(''.join(json.dumps(e, sort_keys=True, allow_nan=False)+'\n' for e in events))
    render = next((out/'renders'/profile/'beauty'/'video.mp4' for profile in ('final', 'preview')
                   if (out/'renders'/profile/'beauty'/'video.mp4').is_file()), None)
    if render is not None:
        rendered = read(render.with_name('render.json'))
        expected = {'source_hash': source_hash, 'states_hash': inputs['physics_states.jsonl'],
                    'video_hash': digest(render), 'fps': fps, 'frame_count': round(duration*fps),
                    'returncode': 0}
        if any(rendered.get(key) != value for key, value in expected.items()):
            raise ValueError('render lineage/cadence does not match finalized scene and states')
        shutil.copyfile(render, out/'preview.mp4')
    manifest = record('SceneManifest', scene_id, source_hash=source_hash,
                      render_hash=digest(render) if render else None, generator_version=VERSION,
                      fps=fps, fps_base=1, start_frame=1, duration_s=duration, units='metres', up_axis='Z',
                      handedness='right', quaternion_order='xyzw', matrix_layout='row_major_column_vectors',
                      camera=production['camera'], objects=[{'object_id': s['object_id'],
                      'sonic_identity_id': s['sonic_identity_id']} for s in specs])
    roles = {'roles_version': 'blender-object-roles-1', 'scene_id': scene_id,
             'scored_object_ids': [s['object_id'] for s in specs if s['scored']],
             'objects': [{'object_id': s['object_id'], 'sonic_identity_id': s['sonic_identity_id'],
                          'role': s['role'], 'scored': s['scored'], 'mode': s['mode']} for s in specs],
             'provenance': prov, 'approval': None}
    dump(out/'manifest.json', manifest)
    dump(out/'object_roles.json', roles)
    dump(out/'geometry.json', {'geometry_version': 'blender-geometry-1', 'objects': list(static.values()),
         'pairs': pairs, 'event_details': details, 'substeps': hz//fps,
         'end_convention': 'render [0,duration), audit includes right endpoint',
         'browser_conversion': '(x,y,z) Blender -> (x,z,-y) browser Y-up; determinant +1',
         'simulation': production['motion_mode'], 'production_lineage': production.get('lineage'),
         'source_inputs': inputs,
         'contact_uncertainty': 'positive contact envelope = frozen pair tolerance + both collision margins; negative penetration cap unchanged; no force claim',
         'validation_evidence': validation,
         'substep_limit': 'sampled transforms; near-miss bounds assume shortest rotation and translation between samples',
         'uncertified_events': unknown})
    dump(out/'summary.json', {'summary_version': 'blender-summary-1', 'scene': manifest,
         'objects': list(summaries.values()), 'events': events, 'event_details': details, 'provenance': prov})
    # Explicit immutable inputs/outputs only: later job logs, review/QA reports,
    # scratch renders, and the index itself cannot invalidate the accepted bytes.
    names = [*input_files, 'manifest.json', 'object_states.jsonl', 'interactions.jsonl',
             'object_roles.json', 'geometry.json', 'summary.json']
    for name in ('config.json', 'replay_states.jsonl'):
        if (out/name).is_file():
            names.append(name)
    if render:
        names.extend(['preview.mp4', str(render.relative_to(out)), str(render.with_name('render.json').relative_to(out))])
    if (out/'bake.json').is_file():
        for name, expected in read(out/'bake.json').get('cache_hashes', {}).items():
            path = (out/name).resolve()
            if not path.is_relative_to(out) or digest(path) != expected:
                raise ValueError('bake cache escapes bundle or differs from sealed index')
            names.append(name)
    if any(digest(out/name) != expected for name, expected in inputs.items()):
        raise RuntimeError('production input evidence changed during export')
    dump(out/'bundle_hashes.json', {'hash_version': 'sha256-persisted-bytes-1',
         'files': {name: digest(out/name) for name in sorted(set(names))}})
    return {'status': 'EXPORTED_NOT_YET_VALIDATED', 'manifest': str(out/'manifest.json'),
            'summary': str(out/'summary.json'), 'object_state_count': len(samples)*len(specs),
            'interaction_count': len(events),
            'certified_interval_contacts': len(interval_report['contacts']) if interval_report else 0,
            'certified_supported_releases': len(interval_report.get('releases', [])) if interval_report else 0, 'render': str(render) if render else None,
            'physical_impact_claim': False, 'approval': None}
