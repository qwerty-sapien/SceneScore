import json
from pathlib import Path

import pytest

from modules.muse.acquisition.tests.helpers import metadata
from modules.muse.baseline.causal import record, stamp
from modules.muse.runtime import MusicContext, RuntimeAdapter, clock_mapping, convert
from modules.muse.runtime.dispatch import attach_receipt, dispatch
from modules.muse.evaluation.latency import intervals, summarize
from scenescore.contracts import validate


def runtime(source="synthetic"):
    meta = metadata()
    meta["provenance"]["source_mode"] = source
    # Test fixture identity only. This test assertion is not hardware evidence.
    if source == "real_device":
        meta["hardware_verified"] = True
    r = RuntimeAdapter(meta, "device-test")
    mapping = clock_mapping(identifier="mapping-test", provenance=meta["provenance"],
        source_clock="device", destination_clock="audio", source_epoch="device-test",
        destination_epoch="transport-0", anchors=[(0, 10), (10, 20)],
        uncertainty_s=.001, valid_from_s=0, valid_until_s=60)
    r.configure(MusicContext("a" * 64, "motion-test", 2,
        {"master_gain_db": -18, "articulation": "score", "expression_preset": "neutral"}), mapping, "host-test")
    r.arm(1)
    return r


def candidate(r, index, onset, duration=.12, quality="good"):
    c = record("BlinkCandidate", f"candidate-{index}", r.metadata, r.config)
    c.update(start=stamp(onset, r.device_epoch), end=stamp(onset + duration, r.device_epoch),
        model_version=r.model_version, score=6.0, score_type="uncalibrated",
        quality={"state": quality, "reason": None if quality == "good" else "fixture_quality_loss"})
    return c


def pair(r, number=0, start=2):
    assert not r.feed(candidate(r, number, start), start + 100)
    assert not r.feed(candidate(r, number + 1, start + .3), start + 100.3)
    return r.advance(start + .920001, start + 100.920001)[0]


def run_case(case):
    r, results = runtime(), []
    faults = case.get("fault", {})
    fault_at = faults.get("dropout_at_s", faults.get("quality_loss_at_s"))
    for n, (onset, duration) in enumerate(case["blinks_s"]):
        # Close a prior pair only if closure precedes the next waveform onset.
        # Never poll a fake idle clock through an active third blink.
        if r.grammar.pending:
            close = r.grammar.pending[-1]["end"]["seconds"] + r.config.max_gap_s + .000001
            if close < onset and close >= r.last_device_s:
                results.extend(r.advance(close, 100 + close))
        if fault_at is not None and fault_at <= onset + duration:
            r.fault("dropout" if "dropout_at_s" in faults else "quality_loss", fault_at)
            fault_at = None
        results.extend(r.feed(candidate(r, n, onset, duration), 100 + onset + duration))
    final = max(r.last_device_s, case["blinks_s"][-1][0] + case["blinks_s"][-1][1]) + .500001
    results.extend(r.advance(final, 100 + final))
    return [item["envelope"] for item in results if item["envelope"] and item["envelope"]["action"]["status"] == "queued"]


def test_no_prefix_double_and_final_end_closure():
    r = runtime()
    assert not r.feed(candidate(r, 0, 2), 102)
    assert not r.feed(candidate(r, 1, 2.3), 102.3)
    assert not r.advance(2.92, 102.92)
    assert r.feed(candidate(r, 2, 2.93), 102.93)[0]["envelope"]  # independent blink after closure
    # Starting just after the closure threshold may accept the prior double:
    # the actual triple exclusion window is end + max_gap, not unlimited.


def test_triple_within_window_emits_no_control():
    r = runtime()
    for n, onset in enumerate((2, 2.3, 2.6)):
        assert not r.feed(candidate(r, n, onset), onset + 100)
    assert r.advance(3.3, 103.3)[0]["reason"] == "single_triple_or_ambiguous_train"


def test_envelope_maps_decision_preserves_lanes_and_metadata():
    result = pair(runtime())
    e, a = result["envelope"], result["envelope"]["action"]
    validate(a)
    assert e["timing"]["t0_final_blink_s"] == pytest.approx(2.42)
    assert e["timing"]["t1_decision_s"] == pytest.approx(2.920001)
    assert e["timing"]["t3_request_s"] == pytest.approx(12.920001)
    assert a["before"] == a["after"]
    assert "model_version" not in a and "samples" not in json.dumps(e)
    assert result["reason"] is None


@pytest.mark.parametrize("fault", ["dropout", "quality_loss", "reconnect", "refit", "model_reload"])
def test_fault_clears_partial_requires_warmup_and_explicit_rearm(fault):
    r = runtime()
    r.feed(candidate(r, 0, 2), 102)
    r.fault(fault, 2.15)
    assert not r.grammar.pending and not r.armed
    with pytest.raises(ValueError, match="warmup_or_rearm_required"):
        r.arm(2.5)
    assert r.feed(candidate(r, 1, 2.3), 102.3)[0]["reason"] == "warmup_or_rearm_required"
    assert not r.advance(3.2, 103.2)
    assert not r.armed
    r.arm(3.3)
    assert pair(r, number=2, start=4)["envelope"]


def test_duplicate_gesture_survives_reset_and_capacity_is_bounded():
    r = runtime()
    r.feed(candidate(r, 0, 2), 102)
    r.feed(candidate(r, 1, 2.3), 102.3)
    gesture = r.grammar.advance(2.93)[0]
    assert r.accept(gesture, 102.93)["envelope"]
    assert r.accept(gesture, 102.94)["reason"] == "duplicate"
    renamed = {**gesture, "id": "renamed-same-blinks"}
    assert r.accept(renamed, 102.94)["reason"] == "duplicate"
    r.disarm(3)
    r.arm(4)
    assert r.accept(gesture, 104)["reason"] == "duplicate"
    r.seen_candidates = {str(i) for i in range(4096)}
    assert r.feed(candidate(r, 7, 5), 105)[0]["reason"] == "dedup_capacity_rearm_insufficient"


def test_clock_expiry_epochs_uncertainty_and_affine_rate():
    r = runtime()
    m = r.mapping
    assert convert(m, stamp(3, "device-test"), destination_clock="audio", destination_epoch="transport-0")["seconds"] == 13
    for modified, ts, epoch in [(m, stamp(61, "device-test"), "transport-0"),
                              (m, stamp(3, "old-device"), "transport-0"),
                              (m, stamp(3, "device-test"), "transport-1"),
                              ({**m, "uncertainty_s": .021}, stamp(3, "device-test"), "transport-0")]:
        with pytest.raises(ValueError, match="unmapped_or_stale_clock"):
            convert(modified, ts, destination_clock="audio", destination_epoch=epoch)
    r.mapping["valid_until_s"] = 2.9
    assert pair(r)["reason"] == "unmapped_or_stale_clock"


def test_all_sources_use_identical_adapter_and_only_provenance_changes():
    normalized = []
    for source in ("real_device", "replay", "synthetic", "keyboard"):
        envelope = pair(runtime(source))["envelope"]
        assert envelope["action"]["provenance"]["source_mode"] == source
        envelope["action"]["provenance"]["source_mode"] = "synthetic"
        normalized.append(json.dumps(envelope, sort_keys=True))
    assert len(set(normalized)) == 1


def test_suppression_not_promoted_and_receipt_uses_explicit_audio_arrival():
    r = runtime()
    r.context = MusicContext(None, "motion-test", 2, r.context.lanes)
    e = pair(r)["envelope"]
    assert e["action"]["status"] == "suppressed" and e["action"]["reason"] == "stale_plan"
    calls = []
    def target(action, audio, scene):
        calls.append(action)
        return {"id": action["id"], "status": "suppressed", "reason": action["reason"],
                "audio_received_s": audio, "boundary_s": 7}
    result = dispatch(e, target, audio_now_s=13, scene_now_s=3)
    assert len(calls) == 1 and result["decision"]["reason"] == "stale_plan"
    assert result["envelope"]["timing"]["t6_boundary_s"] is None
    assert result["envelope"]["timing"]["t5_ack_onset_s"] is None


def test_ladder_never_subtracts_device_from_host():
    e = pair(runtime())["envelope"]
    e = attach_receipt(e, {"id": e["action"]["id"], "audio_received_s": 12.921,
        "ack_onset_audio_s": 13.0, "arrival_audio_s": 15.1})
    observed = intervals(e)
    assert observed["intervals_ms"]["final_blink_to_decision_ms"] == pytest.approx(500.001)
    assert observed["intervals_ms"]["receipt_to_scheduled_ack_ms"] == pytest.approx(79)
    assert observed["intervals_ms"]["dispatch_after_decision_ms"] is None
    assert observed["acoustic_latency_ms"] is None
    assert summarize([e])["intervals"]["receipt_to_scheduled_ack_ms"]["n"] == 1


def test_original_pack_conflicts_remain_explicit_and_corrected_cases_match():
    doc = json.loads((Path(__file__).parents[2] / "evaluation/grammar-semantics-v1.json").read_text())
    for case in doc["original_cases"]:
        assert len(run_case(case)) == case["repository_expected_actions"], case["id"]
    assert [case["id"] for case in doc["original_cases"]
            if case["pack_expected_actions"] != case["repository_expected_actions"]] == ["P2", "N3", "N8"]
    for case in doc["corrected_cases"]:
        assert len(run_case(case)) == case["repository_expected_actions"], case["id"]
