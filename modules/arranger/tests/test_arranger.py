from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scenescore.contracts import content_hash, validate
from modules.arranger.core import (ApprovedSession, Context, Policy, baseline, compile_preview, digest,
                                  encoded, exact_diff, import_plan, motion_direction, validate_plan)
from modules.arranger.provider import Planner, ProviderError, cache_key, public_summary
from modules.arranger.api import router

ROOT = Path(__file__).resolve().parents[3]
BRIEF = "Original blues/ragtime swing; restrained bossa accompaniment"


def record(kind):
    return json.loads((ROOT / "fixtures/contracts" / (kind+".json")).read_text())


@pytest.fixture
def ctx():
    scene, comp, groove = record("SceneManifest"), record("CompositionSpec"), record("BrushGroove")
    scene["duration_s"] = 10
    comp["length_ticks"] *= 4
    comp["harmony"][0]["duration_ticks"] *= 4
    comp["notes"] = [dict(n, start_tick=n["start_tick"]+bar*3840) for bar in range(4) for n in comp["notes"]]
    states = []
    for obj in ("a", "b"):
        for i in range(101):
            state = record("ObjectState")
            state.update(id=f"{obj}:{i}", object_id=obj, scene_id=scene["id"], scene_time_s=i/10, frame=1+i*3,
                         velocity_m_s=[0, 0, .2 if obj == "a" else -.2])
            states.append(state)
    event = record("InteractionEvent")
    event.update(id="hit", onset_s=2, duration_s=.1, pair=["a", "b"], pair_id="a|b", scene_id=scene["id"],
                 event_type="collision", physical_impact=False, method="scripted")
    return Context(scene, states, [event], comp, groove)


def approval(plan):
    a = record("Approval")
    a.update(plan_id=plan["id"], approved_payload_sha256=content_hash(encoded(plan)),
             input_hashes=[plan["scene_hash"], plan["composition_hash"]], decision="approved")
    a["provenance"]["source_mode"] = "synthetic"
    return a


def proposal(ctx):
    p = baseline(ctx)
    return {"explanation": "Synthetic mock; not a live model judgment.", "object_ids": ["a"], "event_ids": ["hit"],
            **{k: p[k] for k in ("groove_id", "register_min", "register_max", "mappings")}}


def transport_for(ctx, *, status=200, response_status="completed", refusal=False, edit=None):
    calls = []
    def transport(path, body, key, timeout):
        calls.append((path, body))
        if path.startswith("models/"):
            return {"status": 200, "body": {"id": "fixture-model"}}
        p = proposal(ctx)
        if edit:
            edit(p)
        content = {"type": "refusal", "refusal": "fixture"} if refusal else {"type": "output_text", "text": json.dumps(p)}
        return {"status": status, "body": {"status": response_status, "output": [{"type": "message", "content": [content]}]}}
    return transport, calls


def test_compile_canonical_and_exact_foley(ctx):
    plan = baseline(ctx)
    events = compile_preview(ctx, plan)
    assert events == compile_preview(ctx, plan)
    assert len(events) == 25
    for e in events:
        validate(e)
    hit = next(e for e in events if e["event_type"] == "foley")
    assert hit["resolved_time_s"] == hit["scene_time_s"] == 2
    assert not hit["swing_applied"]
    assert set(m["object_id"] for m in plan["motif_owners"]) == {"a", "b"}


def test_manual_roundtrip_and_stale_byte_rejection(ctx):
    p = baseline(ctx)
    assert import_plan(encoded(p), ctx, Policy(), BRIEF) == p
    a = approval(p)
    ApprovedSession(encoded(p), a, ctx)
    with pytest.raises(ValueError, match="stale_or_unapproved"):
        ApprovedSession(encoded(p)+b" ", a, ctx)
    p["register_max"] -= 1
    with pytest.raises(ValueError, match="stale_or_unapproved"):
        ApprovedSession(encoded(p), a, ctx)


@pytest.mark.parametrize("change,reason", [
    (lambda p: p.update(groove_id="missing"), "unknown_groove"),
    (lambda p: p.update(register_min=0), "unsafe_register"),
    (lambda p: p["mappings"].append(p["mappings"][0]), "conflicting"),
    (lambda p: p["palette_ids"].append("shell-command"), "unknown_or_missing_palette"),
    (lambda p: p["mappings"][0].update(output_max=10), "lane_output_bounds"),
    (lambda p: p.update(scene_hash="0"*64), "stale_asset_hash"),
    (lambda p: p["motif_owners"][0].update(object_id="missing"), "unknown_or_missing_object"),
])
def test_semantically_invalid_plans(ctx, change, reason):
    p = baseline(ctx)
    change(p)
    with pytest.raises(ValueError, match=reason):
        validate_plan(p, ctx, Policy(), BRIEF)


def test_policy_changes_invalidate_approval(ctx):
    p = baseline(ctx)
    with pytest.raises(ValueError, match="stale_policy"):
        ApprovedSession(encoded(p), approval(p), ctx, Policy(gain_db=-9))


def test_changed_trajectory_invalidates_cache(ctx):
    a = cache_key(ctx, Policy(), BRIEF, "fixture-model", 42)
    ctx.states[5]["velocity_m_s"][2] = 1
    assert cache_key(ctx, Policy(), BRIEF, "fixture-model", 42) != a


def test_changed_interaction_is_region_local(ctx):
    before = compile_preview(ctx, baseline(ctx))
    ctx.interactions[0]["onset_s"] = 2.1
    after = compile_preview(ctx, baseline(ctx))
    def musical(e):
        return {k: v for k, v in e.items() if k not in ("provenance", "plan_id")}
    b = {e["id"]: musical(e) for e in before}
    a = {e["id"]: musical(e) for e in after}
    assert [ident for ident in a if a[ident] != b[ident]] == ["foley:hit"]


def test_motion_causal_signed_and_stationary(ctx):
    p = baseline(ctx)
    assert motion_direction(ctx, p, 1) == 2
    ctx.states[-1]["velocity_m_s"][2] = -1000  # future/other object irrelevant
    assert motion_direction(ctx, p, 1) == 2
    for s in ctx.states:
        if s["object_id"] == "a":
            s["velocity_m_s"][2] = -.2
    assert motion_direction(ctx, p, 1) == -2
    for s in ctx.states:
        s["velocity_m_s"] = [0, 0, 0]
    assert motion_direction(ctx, p, 1) == 0


def test_modulation_preserves_expression_and_nonpitched(ctx):
    p = baseline(ctx)
    session = ApprovedSession(encoded(p), approval(p), ctx)
    before = deepcopy(session.events)
    result = session.request("key-1", 1)
    assert result["signed_semitones"] == 2 and result["tonic_pc"] == 2
    after = {e["id"]: e for e in session.events}
    for e in before:
        other = after[e["id"]]
        assert all(e[k] == other[k] for k in ("dynamics_db", "velocity", "articulation", "timbre_id"))
        if e["event_type"] != "note":
            assert e == other
    assert any(e["phrasing"] == "new-tonic-arrival" for e in session.events)
    assert any(e["phrasing"] == "new-dominant" for e in session.events)
    assert session.request("key-1", 1)["reason"] == "duplicate_request"
    assert session.request("key-2", 1.1)["reason"] == "boundary_already_queued"
    assert session.request("triple", 4, count=3)["status"] == "suppressed"
    assert session.request("single", 4, count=1)["status"] == "suppressed"
    second = session.request("key-3", 4)
    assert second["tonic_pc"] == 4
    assert all(e["midi_pitch"] is None or 28 <= e["midi_pitch"] <= 96 for e in session.events)


def test_smoothing_lane_edits_and_silence(ctx):
    p = baseline(ctx)
    events = compile_preview(ctx, p)
    # Musical spaces survive; no note-on generator runs once per geometry sample.
    assert len([e for e in events if e["object_id"] == "a" and e["event_type"] == "note"]) == len(ctx.composition["notes"])
    p["mappings"][-1].update(output_min=0, output_max=0)
    modified = compile_preview(ctx, p)
    assert any(a["midi_pitch"] != b["midi_pitch"] for a, b in zip(events, modified))
    assert exact_diff(baseline(ctx), p)[0]["field"] == "mappings"


def test_missing_config_no_call(ctx, tmp_path):
    def unexpected(*args):
        raise AssertionError("network")
    result = Planner(tmp_path, transport=unexpected, environ={}).propose(ctx)
    assert result["live_api_status"] == "NOT_RUN"
    assert result["source_mode"] == "manual_plan"


def test_mock_proposal_cache_revalidation_and_invalidation(ctx, tmp_path):
    transport, calls = transport_for(ctx)
    planner = Planner(tmp_path, transport=transport, environ={"OPENAI_API_KEY": "fixture", "OPENAI_MODEL": "fixture-model"})
    first = planner.propose(ctx)
    assert first["source_mode"] == "live_gpt"  # mock transport only, not live evidence
    second = planner.propose(ctx)
    assert second["source_mode"] == "cached_gpt" and len(calls) == 2
    cache = next(tmp_path.glob("*.json"))
    payload = json.loads(cache.read_bytes())
    payload["proposals"][0]["groove_id"] = "missing"
    payload["payload_hash"] = digest(payload["proposals"])
    cache.write_bytes(encoded(payload))
    assert planner.propose(ctx)["reason"] == "unknown_groove"
    assert calls[1][1]["model"] == "fixture-model"
    assert calls[1][1]["store"] is False
    assert "tools" not in calls[1][1]


@pytest.mark.parametrize("kwargs,reason", [
    ({"status": 404}, "http_404"), ({"status": 429}, "http_429"),
    ({"response_status": "incomplete"}, "incomplete_or_truncated"),
    ({"refusal": True}, "refusal"),
    ({"edit": lambda p: p.update(register_min=127)}, "register_bounds"),
    ({"edit": lambda p: p.update(groove_id="unknown")}, "unknown_groove"),
    ({"edit": lambda p: p.update(event_ids=["fake-event"])}, "unknown_explanation_reference"),
    ({"edit": lambda p: p.update(command="sh")}, "proposal_schema_invalid"),
])
def test_provider_failure_falls_back_without_activation(ctx, tmp_path, kwargs, reason):
    transport, calls = transport_for(ctx, **kwargs)
    result = Planner(tmp_path, transport=transport, environ={"OPENAI_API_KEY": "fixture", "OPENAI_MODEL": "fixture-model"}).propose(ctx)
    assert result["status"] == "fallback" and reason in result["reason"]
    assert result["active_plan_changed"] is False
    assert len(calls) <= 3


def test_timeout_and_candidate_bound(ctx, tmp_path):
    def timeout(*args):
        raise ProviderError("timeout")
    p = Planner(tmp_path, transport=timeout, environ={"OPENAI_API_KEY": "fixture", "OPENAI_MODEL": "fixture-model"})
    assert p.propose(ctx)["reason"] == "timeout"
    with pytest.raises(ValueError, match="candidate_limit"):
        p.propose(ctx, candidate_count=4)
    assert p.lock.acquire(False)
    assert p.propose(ctx)["status"] == "busy"
    p.lock.release()


def test_summary_excludes_acquisition_and_metadata(ctx):
    ctx.scene["provenance"]["creator"] = "secret-device-identifier"
    summary = encoded(public_summary(ctx, BRIEF))
    assert b"secret-device" not in summary
    assert b"provenance" not in summary
    assert b"velocity_m_s" in summary


def test_router_validates_without_side_effects(ctx):
    app = FastAPI()
    app.include_router(router, prefix="/arranger")
    client = TestClient(app)
    response = client.post("/arranger/preview", json={"context": asdict(ctx)})
    assert response.status_code == 200
    assert response.json()["audition_status"] == "AUDITION_PENDING"
    assert client.post("/arranger/preview", json={}).status_code == 422


def test_golden(ctx):
    plan = baseline(ctx)
    payload = {"context": asdict(ctx), "policy": asdict(Policy()), "brief": BRIEF}
    events = compile_preview(ctx, plan)
    expected = json.loads((Path(__file__).parents[1]/"golden/fixture.json").read_text())
    assert {"plan_hash": digest(plan), "events_hash": digest(events), "event_count": len(events)} == expected
    assert payload["context"]["scene"]["provenance"]["source_mode"] == "synthetic"


def test_hysteresis_does_not_chatter():
    from modules.arranger.core import Hysteresis
    gate = Hysteresis()
    assert [gate.update(v) for v in [.1, .7, .59, .41, .55, .39, .5]] == [False, True, True, True, True, False, False]


def test_active_payload_is_defensive_copy(ctx):
    p = baseline(ctx)
    session = ApprovedSession(encoded(p), approval(p), ctx)
    session.plan["register_min"] = 0
    session.events.clear()
    assert session.plan["register_min"] == 28
    assert session.events
    assert session.request("late", 4)["status"] == "prepared"
    assert session.request("early", 1)["reason"] == "out_of_order_request"


def test_near_miss_and_separation_have_audible_bounded_changes(ctx):
    before = compile_preview(ctx, baseline(ctx))
    event = ctx.interactions[0]
    event.update(event_type="near_miss", onset_s=2.6, duration_s=.1, surface_gap_m=.05, uncertainty_m=.001)
    near = compile_preview(ctx, baseline(ctx))
    assert not any(e["event_type"] == "foley" for e in near)
    assert any(e["phrasing"] in ("cadence-withheld", "delayed-resolution") for e in near)
    event.update(event_type="separation", onset_s=2.4, duration_s=.5)
    sep = compile_preview(ctx, baseline(ctx))
    assert any(e["dynamics_db"] < -12 for e in sep)
    assert all(e["dynamics_db"] >= -24 for e in sep)
    assert len(sep) == len(before)-1


def test_input_record_order_does_not_change_approved_output(ctx):
    ctx.states[0]["surface_area_m2"] = .1
    ctx.states[100]["surface_area_m2"] = 10
    p = baseline(ctx)
    first = compile_preview(ctx, p)
    ctx.states.reverse()
    assert first == compile_preview(ctx, p)


def test_minor_transition_arrives_minor(ctx):
    ctx.composition["key_map"][0]["mode"] = "minor"
    p = baseline(ctx)
    session = ApprovedSession(encoded(p), approval(p), ctx)
    result = session.request("minor", 1)
    assert result["tonic_pc"] == 2 and result["mode"] == "minor"
    notes = [e["midi_pitch"] % 12 for e in session.events if e["phrasing"] == "new-tonic-arrival"]
    assert set(notes) == {2, 5, 9}


def test_approved_context_is_defensive_copy(ctx):
    p = baseline(ctx)
    session = ApprovedSession(encoded(p), approval(p), ctx)
    for row in session.ctx.states:
        row["velocity_m_s"] = [0, 0, -.2]
    assert session.request("unchanged", 1)["signed_semitones"] == 2
