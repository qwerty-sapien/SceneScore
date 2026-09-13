"""Prepare a new piano-led staircase audition; preserve all source bundles/media."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from modules.arranger.core import encoded
from modules.blender.production.playback import create_playback_window
from scenescore.contracts import validate

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'apps/web/public'
VERSION = 'scene-piano-mix-1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(source, source_hash):
    b = deepcopy(source)
    plan = json.loads(b['plan_bytes'])
    plan['id'] += ':clean-piano-v1'
    events = []
    for original in b['events']:
        e = deepcopy(original)
        if e['event_type'] == 'brush':
            if e['articulation'] == 'sweep' or 'sustain' in e['articulation']:
                continue  # No continuous hiss in this separately labelled edition.
            e['dynamics_db'] -= 18
        elif e['event_type'] == 'foley':
            e.update(instrument_id='scene_wood_contact_v1', timbre_id='wood-low', duration_s=.12)
        elif e['instrument_id'] == 'keyboard_damped_v1':
            e.update(instrument_id='scene_piano_v1', timbre_id='scene_piano_v1')
        e['plan_id'] = plan['id']
        validate(e)
        events.append(e)
    content_bytes = encoded([{k: v for k, v in e.items() if k != 'plan_id'} for e in events])
    mix = dict(version=VERSION, voice_version='scene-piano-voices-1', default_gain_db=-6,
               source_bundle_sha256=source_hash, events_content_sha256=digest(content_bytes),
               brush_attenuation_db=18, approval=None,
               label='Draft · clean piano, quiet brush taps and scene-timed wooden contacts')
    mix_bytes = encoded(mix)
    plan['palette_ids'] = sorted({e['instrument_id'] for e in events})
    plan['provenance'].update(creator=VERSION, tool_version=VERSION, config_hash=digest(mix_bytes),
                              input_hashes=[b['scene_hash'], b['composition_hash'], source_hash, digest(mix_bytes)])
    plan['uncertainties'].append('Piano-led audition edition; human listening approval pending.')
    validate(plan)
    event_bytes = encoded(events)
    window, window_hash = create_playback_window(event_bytes, b['scene']['duration_s'])
    b.update(id=b['id']+'-clean-piano-v1', video='../blender-review/'+b['video'],
             events=events, events_bytes=event_bytes.decode(), source_events_bytes=event_bytes.decode(),
             events_sha256=digest(event_bytes), plan_bytes=encoded(plan).decode(), plan_sha256=digest(encoded(plan)),
             composition_input_bytes=encoded(dict(composition=b['composition'], groove=b['groove'])).decode(),
             playback_window=window, playback_window_bytes=encoded(window).decode(), playback_window_sha256=window_hash,
             piano_mix=mix, piano_mix_bytes=mix_bytes.decode(), piano_mix_sha256=digest(mix_bytes),
             piano_event_bytes=content_bytes.decode(), approval=None, label=mix['label'])
    return b


def main():
    source_dir = PUBLIC/'blender-review'
    if not (source_dir/'catalog.json').is_file():
        return
    output = PUBLIC/'piano-studio'
    entries = []
    for entry in json.loads((source_dir/'catalog.json').read_text())['entries']:
        if not entry['id'].startswith('05_bouncing_staircase-'):
            continue
        raw = (source_dir/entry['url']).read_bytes()
        if digest(raw) != entry['sha256']:
            raise ValueError('stale_piano_source')
        source = json.loads(raw)
        if digest((source_dir/source['video']).read_bytes()) != source['video_sha256']:
            raise ValueError('stale_piano_video')
        b = prepare(source, digest(raw))
        payload = encoded(b)
        output.mkdir(exist_ok=True)
        name = b['id']+'.json'
        target = output/name
        if not target.is_file() or digest(target.read_bytes()) != digest(payload):
            target.write_bytes(payload)
        entries.append({**entry, 'id':b['id'], 'url':name, 'sha256':digest(payload), 'arrangement':'clean-piano'})
    if entries:
        (output/'catalog.json').write_bytes(encoded(dict(version='studio-catalog-1', entries=entries)))
        print(f'Piano editions: {len(entries)} drafts; original bundles unchanged', flush=True)


if __name__ == '__main__':
    main()
