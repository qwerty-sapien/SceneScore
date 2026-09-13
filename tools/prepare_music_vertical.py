"""Prepare the fixed legacy hero as a new, unapproved music-vertical candidate.

This additive CLI never selects another scene, serves an app, renders media, edits
existing assets or creates approval. Exact serialized inputs accompany parsed JSON.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
from types import SimpleNamespace

from scenescore.contracts import validate

VERSION = 'music-vertical-preparation-1'
HERO = Path('artifacts/blender/validated-hero/10_projectile_tower-default')
FREEZE = Path('reports/music-vertical/BASELINE.json')
OUTPUT_ROOT = Path('artifacts/music-vertical')
INPUT_NAMES = ('manifest.json', 'summary.json', 'geometry.json', 'config.json',
               'object_states.jsonl', 'interactions.jsonl', 'bundle_hashes.json', 'preview.mp4')
FOCUS_OBJECT = '10_projectile_tower:tower-2'
MAX_METADATA_BYTES = 64 * 1024 * 1024
MAX_VIDEO_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 96 * 1024 * 1024
MAX_EVENTS = 5000
MAX_RUNTIME_S = 120


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def _dependencies():
    # Import only when executing preparation, so --help works before node 04 lands.
    from modules.arranger import core
    from modules.blender import geometry, summary
    from modules.music import catalog, events, render, transitions
    from modules.music import ornament
    from scenescore import contracts
    return SimpleNamespace(Context=core.Context, compile=core.compile_vertical_preview,
                           source=catalog.build_vertical_score, transition=transitions.vertical_transition_sidecar,
                           table_path=transitions.TABLE_PATH, table_sha256=transitions.TABLE_SHA256,
                           code_paths=[Path(m.__file__) for m in (
                               core, catalog, events, render, transitions, ornament, geometry, summary, contracts)] +
                           [contracts.ROOT / 'contracts/0.1/schema.json'])


def _read(path, maximum):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('missing_symlinked_or_oversized_input:' + path.name)
    return path.read_bytes()


def _decode(value):
    return json.loads(value, parse_constant=lambda token: (_ for _ in ()).throw(ValueError('nonfinite_json:' + token)))


def _lines(raw):
    return [_decode(line) for line in raw.splitlines() if line.strip()]


def _event_check(events, duration, plan):
    if not isinstance(events, list) or not 0 < len(events) <= MAX_EVENTS:
        raise ValueError('prepared_event_budget')
    identifiers = set()
    for event in events:
        validate(event)
        if event['kind'] != 'ScoreEvent' or event['id'] in identifiers:
            raise ValueError('invalid_or_duplicate_prepared_event')
        identifiers.add(event['id'])
        if event['plan_id'] != plan['id'] or event['instrument_id'] not in plan['palette_ids']:
            raise ValueError('unbound_prepared_event')
        if not 0 <= event['resolved_time_s'] < event['resolved_time_s'] + event['duration_s'] <= duration + 1e-9:
            raise ValueError('prepared_event_outside_scene')


def _code_hashes(paths):
    return {str(path.resolve()): sha(path.read_bytes()) for path in paths}


def _midi_payload(events, composition):
    """Bounded SMF1 interchange, with independent tracks for harmony/object voices."""
    from modules.music.render import _track, _varlen

    skipped = {'status': 'not_run', 'path': None}
    if len(composition['tempo_map']) != 1 or composition['tempo_map'][0]['bpm'] != 96:
        return None, {**skipped, 'reason': 'Dedicated MIDI adapter requires the frozen constant 96 BPM.'}
    music = [event for event in events if event['event_type'] != 'foley']
    groups = {}
    for event in music:
        groups.setdefault((event['lane_id'], event['object_id']), []).append(event)
    pitched = [key for key, group in groups.items() if all(e['event_type'] == 'note' for e in group)]
    if len(pitched) > 15:
        return None, {**skipped, 'reason': 'Dedicated MIDI adapter exceeds 15 pitched lane/object tracks.'}
    programs = {'keyboard_damped_v1': 0, 'bass_pluck_v1': 32, 'object_bell_v1': 11}
    brushes = {'sweep': 38, 'tap': 38, 'accented_swish': 40, 'chick': 44}
    channels = iter([number for number in range(16) if number != 9])
    numerator, denominator = composition['meter']
    if denominator & (denominator - 1):
        return None, {**skipped, 'reason': 'Unsupported MIDI meter denominator.'}
    tempo = round(60_000_000 / 96)
    length, ppq = composition['length_ticks'], composition['ppq']
    conductor = [(0, 0, b'\xff\x51\x03' + tempo.to_bytes(3, 'big')),
                 (0, 1, b'\xff\x58\x04' + bytes([numerator, denominator.bit_length() - 1, 24, 8]))]
    tracks, metadata = [_track(conductor, length)], []
    for (lane, object_id), group in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or '')):
        is_pitched = all(e['event_type'] == 'note' for e in group)
        if (not is_pitched and not all(e['event_type'] == 'brush' for e in group)) or (
                is_pitched and any(e['timbre_id'] not in programs for e in group)):
            return None, {**skipped, 'reason': 'Unsupported or mixed MIDI voice type.'}
        channel = next(channels) if is_pitched else 9
        name = (lane + (':' + object_id if object_id else '')).encode()
        data = [(0, 0, b'\xff\x03' + _varlen(len(name)) + name)]
        if is_pitched:
            if len({e['timbre_id'] for e in group}) != 1:
                return None, {**skipped, 'reason': 'MIDI lane changes timbre inside one track.'}
            data.append((0, 1, bytes([0xC0 + channel, programs[group[0]['timbre_id']]])))
        for event in group:
            if not is_pitched and event['articulation'] not in brushes:
                return None, {**skipped, 'reason': 'Unsupported MIDI brush technique.'}
            pitch = event['midi_pitch'] if is_pitched else brushes[event['articulation']]
            # Mirrors current browser gate fractions; MIDI cannot reproduce its synth envelope.
            gate = {'staccato': .45, 'tenuto': .94}.get(event['articulation'], 1.0)
            start = round(event['resolved_time_s'] * 96 / 60 * ppq)
            end = min(length, max(start + 1, round((event['resolved_time_s'] + event['duration_s'] * gate) * 96 / 60 * ppq)))
            if not 0 <= start < end <= length:
                raise ValueError('midi_event_outside_score')
            data += [(start, 3, bytes([0x90 + channel, pitch, event['velocity']])),
                     (end, 2, bytes([0x80 + channel, pitch, 0]))]
        tracks.append(_track(data, length))
        metadata.append({'lane_id': lane, 'object_id': object_id, 'channel_zero_based': channel,
                         'pitched': is_pitched, 'event_count': len(group)})
    payload = b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), ppq) + b''.join(tracks)
    return payload, {'status': 'prepared', 'path': 'score.mid', 'format': 'SMF1', 'tracks': metadata,
                     'tempo_bpm': 96, 'foley_included': False,
                     'reason': 'Editable lane/object MIDI; brush hits and synth envelopes are approximations. '
                               'Canonical events, articulation and scene-time Foley JSON remain authoritative.'}


def prepare_candidate(repo_root, output):
    started = time.monotonic()
    root = Path(repo_root).resolve()
    requested = Path(output)
    if not requested.is_absolute():
        requested = root / requested
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('symlink_output_disallowed')
    output = requested.resolve()
    scope = (root / OUTPUT_ROOT).resolve()
    if output == scope or not output.is_relative_to(scope):
        raise ValueError('output_requires_dedicated_music_vertical_directory')
    if output.exists():
        raise FileExistsError('output_already_exists')
    source_dir = root / HERO
    if source_dir.is_symlink():
        raise ValueError('frozen_scene_symlink_disallowed')
    freeze_raw = _read(root / FREEZE, 1024 * 1024)
    freeze = _decode(freeze_raw)
    if ((freeze.get('duration_s'), freeze.get('fps'), freeze.get('seed'),
         freeze.get('composition_id'), freeze.get('groove_id')) !=
            (30, 8, 42, 'tilted_blue_v1', 'brush_swing_light_v1') or
            Path(freeze.get('scene_dir', '')).resolve() != source_dir.resolve()):
        raise ValueError('frozen_selection_mismatch')
    raw = {name: _read(source_dir / name, MAX_VIDEO_BYTES if name == 'preview.mp4' else MAX_METADATA_BYTES)
           for name in INPUT_NAMES}
    if sum(len(data) for name, data in raw.items() if name != 'preview.mp4') > MAX_METADATA_BYTES:
        raise ValueError('scene_metadata_byte_budget')
    inputs = {str(HERO / name): sha(data) for name, data in raw.items()}
    for name, digest in inputs.items():
        if freeze.get('input_hashes', {}).get(name) != digest:
            raise ValueError('frozen_input_hash_mismatch:' + name)
    scene, summary, geometry = (_decode(raw[name]) for name in ('manifest.json', 'summary.json', 'geometry.json'))
    states, interactions = _lines(raw['object_states.jsonl']), _lines(raw['interactions.jsonl'])
    if len(states) > 30000 or len(interactions) > 512:
        raise ValueError('scene_record_budget')
    if (scene.get('duration_s') != 30 or scene.get('duration_s') > 60 or
            scene.get('fps') != 8 or scene.get('fps_base') != 1 or
            scene.get('render_hash') != sha(raw['preview.mp4'])):
        raise ValueError('frozen_scene_timing_or_video_mismatch')
    if summary.get('scene') != scene or sorted(summary.get('events', []), key=lambda e: e['id']) != sorted(interactions, key=lambda e: e['id']):
        raise ValueError('summary_manifest_or_interactions_mismatch')
    bundle_hashes = _decode(raw['bundle_hashes.json']).get('files', {})
    if any(bundle_hashes.get(name) != sha(raw[name]) for name in INPUT_NAMES if name != 'bundle_hashes.json'):
        raise ValueError('scene_bundle_hash_mismatch')
    deps = _dependencies()
    code_paths = [Path(__file__).resolve(), *deps.code_paths]
    code_hashes = _code_hashes(code_paths)
    score = deps.source()
    if score['sidecar']['source_hashes'] != {
            'composition_sha256': freeze.get('composition_sha256'), 'groove_sha256': freeze.get('groove_sha256')}:
        raise ValueError('frozen_music_source_mismatch')
    composition, groove = score['composition'], score['groove']
    ctx = deps.Context(scene, states, interactions, composition, groove)
    if FOCUS_OBJECT not in ctx.objects:
        raise ValueError('frozen_focus_object_missing')
    mapping_config = {'focus_object_id': FOCUS_OBJECT}
    preview = deps.compile(ctx, geometry=geometry, seed=42, mapping_config=mapping_config)
    if preview.get('approval') is not None or preview.get('audition_status') != 'AUDITION_PENDING':
        raise ValueError('preparation_cannot_create_approval_or_audition')
    if preview.get('duration_s') != scene['duration_s']:
        raise ValueError('mapped_duration_mismatch')
    plan = preview['plan']
    validate(plan)
    plan_bytes = preview['plan_payload'].encode('utf-8')
    if (sha(plan_bytes) != preview['plan_payload_sha256'] or _decode(plan_bytes) != plan or
            plan['scene_hash'] != ctx.scene_hash or plan['composition_hash'] != ctx.composition_hash or
            plan['review_status'] != 'draft'):
        raise ValueError('plan_bytes_or_context_mismatch')
    source_events, events = preview['source_events'], preview['events']
    foley = preview['foley_events']
    unmodified = preview['source_with_foley_events']
    if ([e for e in source_events if e['event_type'] == 'foley'] or
            sorted(unmodified, key=lambda e: e['id']) != sorted([*source_events, *foley], key=lambda e: e['id']) or
            sorted((e for e in events if e['event_type'] == 'foley'), key=lambda e: e['id']) != sorted(foley, key=lambda e: e['id'])):
        raise ValueError('ab_foley_stream_mismatch')
    for sequence in (source_events, unmodified, events):
        _event_check(sequence, scene['duration_s'], plan)
    scene_input_bytes = encoded(ctx.scene_inputs)
    composition_input_bytes = encoded({'composition': composition, 'groove': groove})
    if sha(scene_input_bytes) != ctx.scene_hash or sha(composition_input_bytes) != ctx.composition_hash:
        raise ValueError('exact_context_serialization_mismatch')
    table = _read(Path(deps.table_path), 1024 * 1024)
    if sha(table) != deps.table_sha256:
        raise ValueError('frozen_transition_table_mismatch')
    transition = deps.transition(score['sidecar']['eligible_arrival_ticks'])
    if (transition.get('version') != 'music-vertical-transitions-2' or transition.get('jazz_enabled') is not False or
            transition.get('table_sha256') != sha(table) or transition.get('approval') is not None or
            transition.get('eligible_arrival_ticks') != score['sidecar']['eligible_arrival_ticks']):
        raise ValueError('transition_sidecar_mismatch')
    source_bytes, event_bytes, unmodified_bytes = map(encoded, (source_events, events, unmodified))
    if (preview['provenance'].get('source_events_sha256') != sha(source_bytes) or
            preview['provenance'].get('mapped_events_sha256') != sha(event_bytes) or
            preview['provenance'].get('scene_hash') != ctx.scene_hash or
            preview['provenance'].get('composition_hash') != ctx.composition_hash):
        raise ValueError('mapping_provenance_hash_mismatch')
    binding_bytes = encoded(preview['provenance']['binding'])
    control_input_bytes = encoded({key: value for key, value in preview['control_track'].items()
                                   if key != 'provenance'})
    holds_bytes = encoded(preview['holds'])
    if (sha(binding_bytes) != preview['provenance'].get('binding_sha256') or
            sha(binding_bytes) not in plan['provenance']['input_hashes']):
        raise ValueError('mapping_binding_hash_mismatch')
    if (sha(control_input_bytes) != preview['provenance']['binding'].get('control_track_sha256') or
            sha(holds_bytes) != preview['provenance']['binding'].get('holds_sha256')):
        raise ValueError('mapping_control_or_hold_hash_mismatch')
    inputs.update({str(FREEZE): sha(freeze_raw), 'transition_table': sha(table)})
    labels = {'control_source_mode': 'SYNTHETIC_TEST', 'planning_mode': 'manual_plan',
              'animation_mode': 'LEGACY_SYNTHETIC_ANIMATION', 'live_device': False,
              'browser_measured': False, 'physical_output_measured': False}
    bundle = {
        'version': 'studio-bundle-1', 'preparation_version': VERSION, 'id': 'music-vertical-hero-v1',
        'title': 'Projectile & tower — music vertical', 'variant': 'music-vertical',
        'animation_label': 'LEGACY SYNTHETIC ANIMATION · 8 fps',
        'video': 'preview.mp4', 'video_sha256': sha(raw['preview.mp4']),
        'scene': scene, 'states': states, 'interactions': interactions, 'geometry': geometry,
        'composition': composition, 'groove': groove, 'scene_hash': ctx.scene_hash,
        'composition_hash': ctx.composition_hash, 'scene_input_bytes': scene_input_bytes.decode(),
        'composition_input_bytes': composition_input_bytes.decode(), 'plan': plan,
        'plan_bytes': plan_bytes.decode(), 'plan_sha256': sha(plan_bytes),
        'source_events': source_events, 'source_events_bytes': source_bytes.decode(), 'source_events_sha256': sha(source_bytes),
        'events': events, 'events_bytes': event_bytes.decode(), 'events_sha256': sha(event_bytes),
        'unmodified_events': unmodified, 'unmodified_events_bytes': unmodified_bytes.decode(),
        'unmodified_events_sha256': sha(unmodified_bytes), 'foley_events': foley,
        'comparison_policy': 'same_foley_music_source_vs_mapped',
        'source_sidecar': score['sidecar'], 'mapping_config': mapping_config,
        'control_track': preview['control_track'], 'holds': preview['holds'], 'mapping_audit': preview['audit'],
        'mapping_binding_bytes': binding_bytes.decode(), 'mapping_binding_sha256': sha(binding_bytes),
        'control_track_input_bytes': control_input_bytes.decode(), 'control_track_input_sha256': sha(control_input_bytes),
        'holds_bytes': holds_bytes.decode(), 'holds_sha256': sha(holds_bytes),
        'mapping_provenance': preview['provenance'], 'music_vertical': transition,
        'source': 'SYNTHETIC_TEST', 'planning_mode': 'manual_plan', 'provenance_labels': labels,
        'input_hashes': inputs, 'code_hashes': code_hashes,
        'approval': None, 'audition_status': 'AUDITION_PENDING', 'status': 'DRAFT_NOT_APPROVED',
    }
    midi_bytes, bundle['midi_export'] = _midi_payload(events, composition)
    candidate_bytes = encoded(bundle)
    catalog = {'version': 'studio-catalog-1', 'entries': [
        {'id': bundle['id'], 'title': bundle['title'], 'variant': bundle['variant'],
         'groove': groove['id'], 'url': 'candidate.json', 'sha256': sha(candidate_bytes)}]}
    files = {'candidate.json': candidate_bytes, 'catalog.json': encoded(catalog), 'preview.mp4': raw['preview.mp4'],
             'plan.json': plan_bytes, 'scene-input.json': scene_input_bytes, 'composition-input.json': composition_input_bytes,
             'source-events.json': source_bytes, 'events.json': event_bytes, 'unmodified-events.json': unmodified_bytes,
             'source-score.json': encoded(score), 'source-sidecar.json': encoded(score['sidecar']),
             'control-track.json': encoded(preview['control_track']), 'holds.json': encoded(preview['holds']),
             'mapping-binding.json': binding_bytes, 'control-track-input.json': control_input_bytes,
             'mapping-audit.json': encoded(preview['audit']),
             'mapping.json': encoded({'config': mapping_config, 'provenance': preview['provenance']}),
             'input-hashes.json': encoded(inputs), 'code-hashes.json': encoded(code_hashes),
             'geometry.json': raw['geometry.json'], 'summary.json': raw['summary.json']}
    if midi_bytes is not None:
        files['score.mid'] = midi_bytes
    if sum(map(len, files.values())) > MAX_OUTPUT_BYTES or time.monotonic() - started > MAX_RUNTIME_S:
        raise ValueError('preparation_output_or_runtime_budget')
    if _code_hashes(code_paths) != code_hashes:
        raise ValueError('source_code_changed_during_preparation')
    # No stale input can be silently copied if an owner changed it during compilation.
    for name, original in raw.items():
        if sha(_read(source_dir / name, MAX_VIDEO_BYTES if name == 'preview.mp4' else MAX_METADATA_BYTES)) != sha(original):
            raise ValueError('source_input_changed_during_preparation:' + name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    written = []
    try:
        for name, data in files.items():
            path = output / name
            with path.open('xb') as stream:
                written.append(path)
                stream.write(data)
        manifest = {'version': VERSION, 'candidate_sha256': sha(candidate_bytes),
                    'files': {p.name: sha(p.read_bytes()) for p in written}, 'input_hashes': inputs,
                    'code_hashes': code_hashes, 'provenance_labels': labels,
                    'approval': None, 'audition_status': 'AUDITION_PENDING',
                    'runtime_s': time.monotonic() - started, 'event_count': len(events),
                    'unmodified_event_count': len(unmodified), 'source_event_count': len(source_events)}
        path = output / 'preparation-manifest.json'
        with path.open('xb') as stream:
            written.append(path)
            stream.write(encoded(manifest))
    except BaseException:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        # Remove only our files; preserve any unexpected file added by another task.
        if not any(output.iterdir()):
            output.rmdir()
        raise
    return {'status': 'prepared', 'output': str(output), 'candidate': str(output / 'candidate.json'),
            'candidate_sha256': sha(candidate_bytes), 'events': len(events), 'duration_s': scene['duration_s'],
            'approval': None, 'audition_status': 'AUDITION_PENDING'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out', type=Path, default=OUTPUT_ROOT / 'candidate-v1')
    args = parser.parse_args()
    print(json.dumps(prepare_candidate(args.repo_root, args.out), sort_keys=True))


if __name__ == '__main__':
    main()
