"""Synthetic production-role boundaries; no human approval or audition evidence."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from modules.arranger.core import ApprovedSession, Context, Policy, baseline, compile_preview, encoded, validate_plan
from modules.blender.production.playback import create_playback_window
from scenescore.contracts import content_hash


ROOT = Path(__file__).resolve().parents[3]
BRIEF = 'Original blues/ragtime swing; restrained bossa accompaniment'
FLOOR = '00-floor'


def record(kind):
    return json.loads((ROOT/'fixtures/contracts'/f'{kind}.json').read_text())


def interaction(scene, ident, kind, pair, onset, surface_gap=0.):
    event = record('InteractionEvent')
    pair = sorted(pair)
    event.update(id=ident, scene_id=scene['id'], pair=pair, pair_id='|'.join(pair), event_type=kind,
                 onset_s=onset, duration_s=.1 if kind == 'contact_sustain' else 0.,
                 surface_gap_m=surface_gap, uncertainty_m=.001, method='baked', physical_impact=False)
    return event


@pytest.fixture
def production_context():
    scene, composition, groove = record('SceneManifest'), record('CompositionSpec'), record('BrushGroove')
    scene['duration_s'] = 2
    scene['objects'].insert(0, {'object_id': FLOOR, 'sonic_identity_id': 'silent:floor'})
    composition['length_ticks'] *= 4
    composition['harmony'][0]['duration_ticks'] *= 4
    composition['notes'] = [dict(note, start_tick=note['start_tick']+bar*3840)
                            for bar in range(4) for note in composition['notes']]
    states = []
    for oid in (FLOOR, 'a', 'b'):
        for tick in range(21):
            state = record('ObjectState')
            state.update(id=f'{oid}:{tick}', object_id=oid, scene_id=scene['id'], scene_time_s=tick/10,
                         frame=1+tick*3, velocity_m_s=[0, 0, 0 if oid == FLOOR else .2])
            states.append(state)
    events = [interaction(scene, 'fake-tower-hit', 'contact_onset', ['a', 'b'], .6, .2),
              interaction(scene, 'floor-hit', 'contact_onset', ['a', FLOOR], 1.2),
              interaction(scene, 'floor-sustain', 'contact_sustain', ['a', FLOOR], 1.3),
              interaction(scene, 'floor-release', 'contact_release', ['a', FLOOR], 1.5),
              interaction(scene, 'legacy-collision', 'collision', ['a', 'b'], 1.7)]
    roles = {'roles_version': 'blender-object-roles-1', 'scene_id': scene['id'],
             'scored_object_ids': ['a', 'b'],
             'validated_contact_ids': ['floor-hit', 'floor-sustain', 'floor-release', 'legacy-collision'],
             'objects': [{'object_id': oid, 'scored': oid != FLOOR,
                          'role': 'support' if oid == FLOOR else 'projectile'} for oid in (FLOOR, 'a', 'b')]}
    policy = {'version': 'scene-playback-window-1', 'duration_s': 2, 'frame_count': 60,
              'render_fps': 30, 'final_fade_s': .01, 'original_events_sha256': 'a'*64}
    return Context(scene, states, events, composition, groove, roles, policy)


def fixture_approval(plan):
    approval = record('Approval')
    approval.update(plan_id=plan['id'], approved_payload_sha256=content_hash(encoded(plan)),
                    input_hashes=[plan['scene_hash'], plan['composition_hash']], decision='approved')
    assert approval['reviewer'] == 'synthetic-reviewer-not-real-approval'
    return approval


def test_full_physical_manifest_is_preserved_but_silent_supports_get_no_motif_or_focus(production_context):
    ctx = production_context
    original_scene = deepcopy(ctx.scene)
    plan = baseline(ctx)
    events = compile_preview(ctx, plan)
    assert ctx.scene == original_scene
    assert {o['object_id'] for o in ctx.scene['objects']} == {FLOOR, 'a', 'b'}
    assert {s['object_id'] for s in ctx.states} == {FLOOR, 'a', 'b'}
    assert ctx.objects == ['a', 'b']
    assert {owner['object_id'] for owner in plan['motif_owners']} == {'a', 'b'}
    assert plan['motion_policy']['focus_object_id'] == 'a'
    assert not any(e['event_type'] == 'note' and e['object_id'] == FLOOR for e in events)
    for owner in plan['motif_owners']:
        identity = next(o['sonic_identity_id'] for o in ctx.scene['objects'] if o['object_id'] == owner['object_id'])
        assert owner['motif_id'] == 'motif-'+identity


@pytest.mark.parametrize('change, reason', [('focus', 'motion_policy_mismatch'), ('owner', 'unknown_or_missing_object')])
def test_silent_support_cannot_be_inserted_as_plan_focus_or_owner(production_context, change, reason):
    plan = baseline(production_context)
    if change == 'focus':
        plan['motion_policy']['focus_object_id'] = FLOOR
    else:
        plan['motif_owners'][0]['object_id'] = FLOOR
    with pytest.raises(ValueError, match=reason):
        validate_plan(plan, production_context, Policy(), BRIEF)


@pytest.mark.parametrize('change', ['scored_set', 'support_metadata', 'contact_allowlist', 'playback_policy'])
def test_roles_and_playback_inputs_invalidate_an_exact_prior_approval(production_context, change):
    ctx = production_context
    plan = baseline(ctx)
    payload, approval = encoded(plan), fixture_approval(plan)
    ApprovedSession(payload, approval, ctx)  # Synthetic contract control, never real approval.
    roles, playback = deepcopy(ctx.role_supplement), deepcopy(ctx.playback_policy)
    if change == 'scored_set':
        roles['scored_object_ids'] = ['a']
    elif change == 'support_metadata':
        roles['objects'][0]['role'] = 'fixed_support'
    elif change == 'contact_allowlist':
        roles['validated_contact_ids'] = []
    else:
        playback['original_events_sha256'] = 'b'*64
    changed = replace(ctx, role_supplement=roles, playback_policy=playback)
    assert changed.scene == ctx.scene and changed.composition_hash == ctx.composition_hash
    assert changed.scene_hash != ctx.scene_hash
    with pytest.raises(ValueError, match='stale_or_unapproved_plan'):
        ApprovedSession(payload, approval, changed)


def test_miss_suppresses_unvalidated_tower_hit_but_retains_only_validated_floor_onset(production_context):
    ctx = production_context
    foley = [e for e in compile_preview(ctx, baseline(ctx)) if e['event_type'] == 'foley']
    assert [e['id'] for e in foley] == ['foley:floor-hit']
    assert foley[0]['scene_time_s'] == foley[0]['resolved_time_s'] == 1.2
    assert foley[0]['articulation'] == 'contact_onset'
    assert foley[0]['lane_id'] == 'contact:00-floor|a'
    assert not foley[0]['swing_applied'] and foley[0]['midi_pitch'] is None


def test_production_without_validated_contacts_emits_no_foley(production_context):
    roles = deepcopy(production_context.role_supplement)
    roles.pop('validated_contact_ids')
    ctx = replace(production_context, role_supplement=roles)
    assert not any(e['event_type'] == 'foley' for e in compile_preview(ctx, baseline(ctx)))


def test_legacy_context_keeps_its_existing_contact_behavior(production_context):
    ctx = replace(production_context, role_supplement=None, playback_policy=None)
    assert set(ctx.objects) == {FLOOR, 'a', 'b'}
    events = compile_preview(ctx, baseline(ctx))
    assert {e['id'] for e in events if e['event_type'] == 'foley'} == {
        'foley:fake-tower-hit', 'foley:floor-hit', 'foley:floor-sustain',
        'foley:floor-release', 'foley:legacy-collision'}


def test_complete_original_score_survives_short_scene_and_projection(production_context):
    ctx = production_context
    composition = deepcopy(ctx.composition)
    events = compile_preview(ctx, baseline(ctx))
    original_bytes = encoded(events)
    window, _ = create_playback_window(original_bytes, ctx.scene['duration_s'], frame_count=60)
    assert ctx.composition == composition
    assert encoded(events) == original_bytes
    for oid in ctx.objects:
        assert len([e for e in events if e['object_id'] == oid and e['event_type'] == 'note']) == len(composition['notes'])
    assert any(e['resolved_time_s'] >= ctx.scene['duration_s'] for e in events)
    assert window['omitted'] and window['truncated']
    crossing = next(e for e in events if e['resolved_time_s'] < 2 < e['resolved_time_s']+e['duration_s'])
    projected = next(p for p in window['projections'] if p['source_event_id'] == crossing['id'])
    assert projected['stop_s'] == 2 < crossing['resolved_time_s']+crossing['duration_s']
    no_window = replace(ctx, playback_policy=None)
    uncropped = compile_preview(no_window, baseline(no_window))
    def music_only(rows):
        return [{k: v for k, v in e.items() if k not in ('provenance', 'plan_id')} for e in rows]
    assert music_only(events) == music_only(uncropped)


@pytest.mark.parametrize('bad_roles', [None, [], ['a', 'a'], ['unknown']])
def test_invalid_or_stale_production_roles_do_not_fall_back_to_all_bodies(production_context, bad_roles):
    roles = deepcopy(production_context.role_supplement)
    if bad_roles is None:
        roles['scene_id'] = 'previous-scene'
        expected = 'stale_object_roles'
    else:
        roles['scored_object_ids'] = bad_roles
        expected = 'invalid_scored_object_roles'
    with pytest.raises(ValueError, match=expected):
        replace(production_context, role_supplement=roles)


@pytest.mark.parametrize('field',['handoff_sha256','features_sha256','handoff_index_sha256'])
def test_motion_handoff_changes_invalidate_exact_plan(production_context,field):
    binding={'version':'scene-music-input-binding-1','handoff_sha256':'a'*64,
             'features_sha256':'b'*64,'handoff_index_sha256':'c'*64}
    ctx=replace(production_context,music_handoff_binding=binding)
    plan=baseline(ctx)
    changed=replace(ctx,music_handoff_binding={**binding,field:'d'*64})
    assert changed.scene_hash!=ctx.scene_hash
    assert changed.composition_hash==ctx.composition_hash
    with pytest.raises(ValueError):
        validate_plan(plan,changed,Policy(),BRIEF)
