"""Musical/event regressions, independent of expensive full scene preparation."""

from copy import deepcopy
import json
from pathlib import Path
import pytest
from modules.arranger.collision_riffs import arrange
from modules.arranger.core import Context, digest, encoded


def source():
    b = json.loads(Path("packages/audio/tests/fixture.json").read_text())["bundle"]
    b["scene"]["duration_s"] = 30
    b["interactions"][0]["event_type"] = "contact_onset"
    b["states"] = b["states"][:2]
    ctx = Context(b["scene"], b["states"], b["interactions"], b["composition"], b["groove"])
    b["scene_hash"] = ctx.scene_hash
    b["scene_input_bytes"] = encoded(ctx.scene_inputs).decode()
    return b


@pytest.fixture(scope="module")
def candidate():
    return arrange(source())


def test_new_melody_has_form_and_keeps_original_untouched(candidate):
    original = source()
    before = deepcopy(original)
    assert arrange(original) == candidate
    assert original == before
    c = candidate["composition"]
    assert c["title"] == "Pocket Workshop" and len(c["harmony"]) == 12
    assert c["length_ticks"] == 46080
    assert c["notes"] != original["composition"]["notes"]
    assert len({n["midi_pitch"] for n in c["notes"]}) >= 12
    assert candidate["approval"] is None
    assert all(e["resolved_time_s"] + e["duration_s"] <= 30 for e in candidate["events"])
    assert len(candidate["events"]) < 350


def test_contact_onsets_get_bounded_knocks_and_owned_replies(candidate):
    refs = candidate["sound_design"]["contact_replies"]
    assert len(refs) == 1
    ref = refs[0]
    events = {e["id"]: e for e in candidate["events"]}
    knock = events[ref["foley_id"]]
    assert knock["duration_s"] == 0.2 and knock["midi_pitch"] is None
    assert knock["instrument_id"] == "wood_contact_v1"
    for i, ident in enumerate(ref["reply_ids"]):
        e = events[ident]
        assert e["resolved_time_s"] == ref["onset_s"] + 0.125 * i
        assert e["object_id"] in candidate["interactions"][0]["pair"]
        assert not e["swing_applied"]


def test_miss_has_no_fabricated_contact_or_static_sustain():
    b = source()
    b["interactions"] = []
    ctx = Context(b["scene"], b["states"], [], b["composition"], b["groove"])
    b["scene_hash"] = ctx.scene_hash
    candidate = arrange(b)
    assert not candidate["sound_design"]["contact_replies"]
    assert not any(e["event_type"] == "foley" for e in candidate["events"])


def test_instrument_or_contact_changes_invalidate_plan(candidate):
    vibes = arrange(source(), "vibraphone")
    assert vibes["plan_sha256"] != candidate["plan_sha256"]
    b = source()
    b["interactions"][0]["onset_s"] += 0.01
    assert arrange(b)["plan_sha256"] != candidate["plan_sha256"]
    assert digest(json.loads(candidate["plan_bytes"])) == candidate["plan_sha256"]
    b = source()
    b["scene"]["duration_s"] = 8
    with pytest.raises(ValueError, match="30_second"):
        arrange(b)


def test_piano_answers_share_harmony_clock_and_leave_contact_space(candidate):
    from modules.arranger.collision_riffs import PHRASES, PIANO_VOICINGS
    from modules.arranger.core import tick_seconds, swung_tick

    comp = candidate["sound_design"]["piano_accompaniment"]
    piano = {e["id"]: e for e in candidate["events"] if e["instrument_id"] == "piano_felt_comp_v1"}
    assert len(piano) >= 50
    assert not any(e["lane_id"].startswith("comp-") for e in candidate["events"])
    c = candidate["composition"]
    for group in comp["groups"]:
        bar, beat = group["bar"], group["beat"]
        assert not any(start <= beat < start + duration - 1e-8 for start, _, duration in PHRASES[bar])
        h = c["harmony"][bar]
        allowed = {(h["root_pc"] + i) % 12 for i in h["intervals_semitones"]}
        for ident in group["event_ids"]:
            e = piano[ident]
            assert e["duration_s"] >= 0.18
            assert e["midi_pitch"] % 12 in allowed
            assert e["object_id"] is None
            assert e["resolved_time_s"] == tick_seconds(c, swung_tick(c, e["start_tick"], True))
            assert (
                abs(
                    tick_seconds(c, swung_tick(c, e["start_tick"] + e["duration_ticks"], True))
                    - e["resolved_time_s"]
                    - e["duration_s"]
                )
                < 0.0005
            )
            for contact in candidate["interactions"]:
                assert (
                    e["resolved_time_s"] + e["duration_s"] <= contact["onset_s"] - 0.06 + 1e-9
                    or e["resolved_time_s"] >= contact["onset_s"] + 0.5
                )
    assert (
        max(abs(a - b) for before, after in zip(PIANO_VOICINGS, PIANO_VOICINGS[1:]) for a, b in zip(before, after)) <= 4
    )
