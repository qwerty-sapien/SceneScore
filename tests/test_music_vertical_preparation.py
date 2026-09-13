"""Preparation assembly tests with labelled synthetic bytes and a fixture mapping adapter.

These tests do not render video, execute the real motion compiler or establish audition.
"""
from copy import deepcopy
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from modules.arranger.core import Context, baseline
from modules.music.catalog import build_vertical_score
from modules.music.events import resolve_events
from tools import prepare_music_vertical as prep

ROOT = Path(__file__).resolve().parents[1]


class FixtureContext(Context):
    @property
    def scene_inputs(self):
        return {'scene': self.scene, 'states': sorted(self.states, key=lambda s: s['id']),
                'interactions': sorted(self.interactions, key=lambda s: s['id'])}


def fixture_compile(ctx, *, geometry, seed, mapping_config):
    assert geometry['evidence_mode'] == 'SYNTHETIC_FIXTURE'
    assert seed == 42 and mapping_config == {'focus_object_id': prep.FOCUS_OBJECT}
    plan = baseline(ctx)
    source = resolve_events(ctx.composition, ctx.groove, plan_id=plan['id'], object_id=prep.FOCUS_OBJECT)
    for event in source:
        if event['articulation'] == 'soft_comp':
            event['lane_id'] = 'harmony-' + str(event['midi_pitch'] % 3)
    plan['palette_ids'] = sorted(set(plan['palette_ids']) | {e['instrument_id'] for e in source})
    plan['motion_policy']['focus_object_id'] = prep.FOCUS_OBJECT
    sweep = next(e for e in source if e['event_type'] == 'brush')
    foley = {**deepcopy(sweep), 'id': 'fixture-foley', 'event_type': 'foley', 'lane_id': 'contact:fixture',
             'instrument_id': 'arranger_contact_noise_v1', 'timbre_id': 'contact-soft',
             'start_tick': None, 'duration_ticks': None, 'resolved_time_s': 1.25,
             'scene_time_s': 1.25, 'duration_s': .1, 'articulation': 'contact_onset'}
    unmodified = sorted([*source, foley], key=lambda e: (e['resolved_time_s'], e['id']))
    mapped = deepcopy(unmodified)
    next(e for e in mapped if e['event_type'] == 'note')['articulation'] = 'legato'
    track, holds = {'mode': 'SYNTHETIC_FIXTURE', 'events': []}, []
    binding = {'control_track_sha256': prep.sha(prep.encoded(track)), 'holds_sha256': prep.sha(prep.encoded(holds))}
    binding_hash = prep.sha(prep.encoded(binding))
    plan['provenance']['input_hashes'].append(binding_hash)
    plan_bytes = prep.encoded(plan)
    track['provenance'] = {'binding_sha256': binding_hash, 'plan_payload_sha256': prep.sha(plan_bytes)}
    return {'plan': plan, 'plan_payload': plan_bytes.decode(), 'plan_payload_sha256': prep.sha(plan_bytes),
            'source_events': source, 'events': mapped, 'foley_events': [foley],
            'source_with_foley_events': unmodified, 'control_track': track,
            'holds': holds, 'audit': {'mode': 'SYNTHETIC_FIXTURE'},
            'provenance': {'mode': 'SYNTHETIC_FIXTURE', 'scene_hash': ctx.scene_hash,
                           'composition_hash': ctx.composition_hash,
                           'binding': binding, 'binding_sha256': binding_hash,
                           'source_events_sha256': prep.sha(prep.encoded(source)),
                           'mapped_events_sha256': prep.sha(prep.encoded(mapped))}, 'duration_s': 30,
            'approval': None, 'audition_status': 'AUDITION_PENDING'}


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    root = tmp_path / 'fixture-repository'
    folder = root / prep.HERO
    folder.mkdir(parents=True)
    scene = json.loads((ROOT / 'fixtures/contracts/SceneManifest.json').read_text())
    scene.update(duration_s=30.0, fps=8, generator_version='synthetic-fixture-not-rendered')
    scene['objects'] = [{'object_id': name, 'sonic_identity_id': 'voice:' + name}
                        for name in (prep.FOCUS_OBJECT, 'fixture-anchor')]
    video = b'SYNTHETIC FIXTURE BYTES; NOT A DECODED OR RENDERED VIDEO'
    scene['render_hash'] = prep.sha(video)
    template = json.loads((ROOT / 'fixtures/contracts/ObjectState.json').read_text())
    states = [{**deepcopy(template), 'id': f'{obj}:{i}', 'object_id': obj,
               'scene_id': scene['id'], 'scene_time_s': float(i * 30), 'frame': i * 240 + 1}
              for obj in (prep.FOCUS_OBJECT, 'fixture-anchor') for i in range(2)]
    raw = {'manifest.json': prep.encoded(scene), 'summary.json': prep.encoded({'scene': scene, 'events': []}),
           'geometry.json': prep.encoded({'evidence_mode': 'SYNTHETIC_FIXTURE'}),
           'config.json': prep.encoded({'seed': 42}),
           'object_states.jsonl': b''.join(prep.encoded(s) for s in states),
           'interactions.jsonl': b'', 'preview.mp4': video}
    raw['bundle_hashes.json'] = prep.encoded({'files': {name: prep.sha(value) for name, value in raw.items()}})
    for name, value in raw.items():
        (folder / name).write_bytes(value)
    source = build_vertical_score()
    freeze = {'scene_dir': str(folder), 'duration_s': 30, 'fps': 8, 'seed': 42,
              'composition_id': 'tilted_blue_v1', 'groove_id': 'brush_swing_light_v1',
              **source['sidecar']['source_hashes'],
              'input_hashes': {str(prep.HERO / name): prep.sha(value) for name, value in raw.items()}}
    (root / prep.FREEZE).parent.mkdir(parents=True)
    (root / prep.FREEZE).write_bytes(prep.encoded(freeze))
    table = tmp_path / 'synthetic-transition-table.json'
    table.write_bytes(b'{"evidence_mode":"SYNTHETIC_FIXTURE"}\n')
    table_hash = prep.sha(table.read_bytes())
    deps = SimpleNamespace(Context=FixtureContext, compile=fixture_compile, source=build_vertical_score,
                           table_path=table, table_sha256=table_hash,
                           code_paths=[Path(__file__)], transition=lambda ticks: {
                               'version': 'music-vertical-transitions-2', 'jazz_enabled': False,
                               'eligible_arrival_ticks': ticks, 'table_sha256': table_hash, 'approval': None})
    monkeypatch.setattr(prep, '_dependencies', lambda: deps)
    return root, folder, deps


def test_candidate_has_exact_bytes_fair_foley_comparison_catalogue_and_editable_score(inputs):
    root, folder, _ = inputs
    original = {p.name: p.read_bytes() for p in folder.iterdir()}
    output = root / prep.OUTPUT_ROOT / 'candidate-fixture'
    result = prep.prepare_candidate(root, output)
    data = json.loads((output / 'candidate.json').read_text())
    for field, hash_field, records in (
            ('scene_input_bytes', 'scene_hash', None), ('composition_input_bytes', 'composition_hash', None),
            ('source_events_bytes', 'source_events_sha256', 'source_events'),
            ('events_bytes', 'events_sha256', 'events'),
            ('unmodified_events_bytes', 'unmodified_events_sha256', 'unmodified_events'),
            ('mapping_binding_bytes', 'mapping_binding_sha256', None),
            ('control_track_input_bytes', 'control_track_input_sha256', None),
            ('holds_bytes', 'holds_sha256', 'holds'),
            ('plan_bytes', 'plan_sha256', 'plan')):
        raw = data[field].encode()
        assert prep.sha(raw) == data[hash_field]
        if records:
            assert json.loads(raw) == data[records]
    assert '"scene_time_s":0.0' in data['scene_input_bytes']
    binding = data['mapping_provenance']['binding']
    assert json.loads(data['mapping_binding_bytes']) == binding
    assert data['mapping_binding_sha256'] in data['plan']['provenance']['input_hashes']
    assert data['control_track_input_sha256'] == binding['control_track_sha256']
    assert data['holds_sha256'] == binding['holds_sha256']
    assert 'provenance' not in json.loads(data['control_track_input_bytes'])
    assert data['provenance_labels']['animation_mode'] == 'LEGACY_SYNTHETIC_ANIMATION'
    assert data['animation_label'] == 'LEGACY SYNTHETIC ANIMATION · 8 fps'
    assert data['source'] == 'SYNTHETIC_TEST' and data['planning_mode'] == 'manual_plan'
    assert data['approval'] is None and data['audition_status'] == 'AUDITION_PENDING'
    assert data['music_vertical']['eligible_arrival_ticks'] == list(range(3840, 46080, 3840))
    assert not data['music_vertical']['jazz_enabled']
    assert data['comparison_policy'] == 'same_foley_music_source_vs_mapped'
    assert not any(e['event_type'] == 'foley' for e in data['source_events'])
    assert [e for e in data['events'] if e['event_type'] == 'foley'] == [
        e for e in data['unmodified_events'] if e['event_type'] == 'foley']
    catalogue = json.loads((output / 'catalog.json').read_text())
    assert catalogue['entries'][0]['url'] == 'candidate.json'
    assert catalogue['entries'][0]['sha256'] == result['candidate_sha256'] == prep.sha((output / 'candidate.json').read_bytes())
    assert (output / 'preview.mp4').read_bytes() == original['preview.mp4']
    assert (output / 'score.mid').read_bytes().startswith(b'MThd')
    midi = (output / 'score.mid').read_bytes()
    _, fmt, track_count, ppq = struct.unpack('>IHHH', midi[4:14])
    tracks = data['midi_export']['tracks']
    assert (fmt, track_count, ppq) == (1, 1 + len(tracks), 960)
    assert {t['lane_id'] for t in tracks} >= {'harmony-0', 'harmony-1', 'harmony-2', 'object_motif'}
    assert all(t['channel_zero_based'] == 9 for t in tracks if not t['pitched'])
    assert len({t['channel_zero_based'] for t in tracks if t['pitched']}) == sum(t['pitched'] for t in tracks)
    assert sum(t['event_count'] for t in tracks) == sum(e['event_type'] != 'foley' for e in data['events'])
    assert (output / 'source-events.json').read_text() == data['source_events_bytes']
    manifest = json.loads((output / 'preparation-manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert prep.sha((output / name).read_bytes()) == expected
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == original


def test_deterministic_candidate_and_existing_output_preserved(inputs):
    root, _, _ = inputs
    one, two = (root / prep.OUTPUT_ROOT / name for name in ('one', 'two'))
    prep.prepare_candidate(root, one)
    prep.prepare_candidate(root, two)
    assert (one / 'candidate.json').read_bytes() == (two / 'candidate.json').read_bytes()
    saved = (one / 'candidate.json').read_bytes()
    with pytest.raises(FileExistsError, match='output_already_exists'):
        prep.prepare_candidate(root, one)
    assert (one / 'candidate.json').read_bytes() == saved


def test_changed_frozen_input_and_outside_scope_are_rejected_before_output(inputs):
    root, folder, _ = inputs
    output = root / prep.OUTPUT_ROOT / 'bad'
    (folder / 'preview.mp4').write_bytes(b'changed')
    with pytest.raises(ValueError, match='frozen_input_hash_mismatch'):
        prep.prepare_candidate(root, output)
    assert not output.exists()
    with pytest.raises(ValueError, match='dedicated_music_vertical'):
        prep.prepare_candidate(root, root / 'apps/web/public/studio')


@pytest.mark.parametrize('mutation,reason', [
    ('plan', 'plan_bytes_or_context_mismatch'), ('duration', 'mapped_duration_mismatch'),
    ('approval', 'cannot_create_approval'), ('foley', 'ab_foley_stream_mismatch'),
    ('events', 'prepared_event_budget'),
    ('hash', 'mapping_provenance_hash_mismatch'),
    ('binding', 'mapping_binding_hash_mismatch'),
    ('controls', 'mapping_control_or_hold_hash_mismatch'),
    ('holds', 'mapping_control_or_hold_hash_mismatch'),
])
def test_invalid_compiler_result_never_leaves_candidate(inputs, mutation, reason):
    root, _, deps = inputs
    def changed(ctx, **kwargs):
        result = fixture_compile(ctx, **kwargs)
        if mutation == 'plan':
            result['plan_payload'] += ' '
        elif mutation == 'duration':
            result['duration_s'] = 61
        elif mutation == 'approval':
            result['approval'] = {'invented': True}
        elif mutation == 'foley':
            result['source_with_foley_events'] = result['source_events']
        elif mutation == 'hash':
            result['provenance']['mapped_events_sha256'] = '0' * 64
        elif mutation == 'binding':
            result['provenance']['binding']['changed'] = True
        elif mutation == 'controls':
            result['control_track']['events'].append({'changed': True})
        elif mutation == 'holds':
            result['holds'].append({'changed': True})
        else:
            result['events'] += [deepcopy(result['source_events'][0]) for _ in range(5001)]
        return result
    deps.compile = changed
    output = root / prep.OUTPUT_ROOT / mutation
    with pytest.raises(ValueError, match=reason):
        prep.prepare_candidate(root, output)
    assert not output.exists()


def test_midi_channel_budget_is_explicit_and_never_silently_drops_lanes():
    score = build_vertical_score()
    event = next(e for e in resolve_events(score['composition'], score['groove']) if e['event_type'] == 'note')
    many = [{**deepcopy(event), 'id': f'fixture-{i}', 'lane_id': f'voice-{i}'} for i in range(16)]
    payload, metadata = prep._midi_payload(many, score['composition'])
    assert payload is None and metadata['status'] == 'not_run'
    assert '15 pitched' in metadata['reason']
