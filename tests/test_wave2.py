"""Phase 2 module boundary checks, not audio/video transport integration."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from modules.arranger.core import Context, baseline, compile_preview
from modules.music.catalog import get_composition, get_groove, list_catalog
from scenescore.contracts import validate
from scenescore.service import app

ROOT = Path(__file__).resolve().parents[1]


def test_mounted_module_health_and_catalog_without_external_jobs():
    with TestClient(app) as client:
        for route in ('/muse/health', '/scene/health', '/music/health', '/arranger/health'):
            assert client.get(route).status_code == 200
        assert client.get('/music/catalog').json() == list_catalog()
        assert client.get('/music/compositions/unknown').status_code == 404
        assert client.get('/scene/summary', params={'bundle': '../outside'}).status_code == 404
        assert client.post('/arranger/preview', json={}).status_code == 422


def test_evaluated_summary_to_original_score_plan_and_exact_foley():
    summary = json.loads((ROOT/'modules/blender/fixtures/hero-summary.json').read_bytes())
    composition = get_composition('tilted_blue_v1')
    groove = get_groove(composition['groove_id'])
    ctx = Context.from_summary(summary, composition, groove)
    plan = baseline(ctx)
    events = compile_preview(ctx, plan)
    assert events == compile_preview(ctx, plan)
    assert {m['object_id'] for m in plan['motif_owners']} == {o['object_id'] for o in summary['scene']['objects']}
    for event in events:
        validate(event)
        if event['event_type'] != 'foley':
            assert event['timbre_id'] in {'keyboard_damped_v1', 'bass_pluck_v1', 'brush_noise_v1'}
        else:
            original = next(e for e in ctx.interactions if 'foley:'+e['id'] == event['id'])
            assert event['scene_time_s'] == event['resolved_time_s'] == original['onset_s']
            assert event['midi_pitch'] is None and not event['swing_applied']
    assert all(e['instrument_id'] in plan['palette_ids'] for e in events)
