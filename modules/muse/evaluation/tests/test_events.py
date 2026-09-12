import math

import pytest

from modules.muse.evaluation.events import candidate_diagnostics, match


def label(i, **overrides):
    return (
        dict(
            id=f"l{i}",
            session_id="s",
            epoch="e",
            final_blink_s=float(i),
            intent="deliberate",
            gesture_count=2,
            certainty="verified",
            eligible=True,
        )
        | overrides
    )


def decision(i, **overrides):
    return (
        dict(id=f"d{i}", session_id="s", epoch="e", final_blink_s=float(i), decision_s=float(i) + 0.2, gesture_count=2)
        | overrides
    )


def test_duplicates_cooldown_and_natural_blinks_count():
    labels = [label(1), label(2, eligible=False), label(3, intent="natural", gesture_count=1)]
    decisions = [decision(1), decision(1, id="duplicate"), decision(3)]
    report = match(labels, decisions, elapsed_s=3600, armed_s=1800)
    assert (report["tp"], report["fp"], report["fn"]) == (1, 2, 1)
    assert report["recall_all"] == 0.5
    assert report["eligible_recall"] == 1
    assert report["false_per_armed_hour"] == 4
    assert report["false_per_elapsed_hour"] == 2
    assert report["confusion"]["natural_1_to_2"] == 1
    assert report["status"] == "PIPELINE_TESTED_ONLY"


@pytest.mark.parametrize(
    "override",
    [{"epoch": "other"}, {"session_id": "other"}, {"gesture_count": 3}, {"decision_s": 0.9, "final_blink_s": 0.8}],
)
def test_no_cross_epoch_session_prefix_or_premature_match(override):
    report = match([label(1)], [decision(1, **override)], elapsed_s=10, armed_s=10)
    assert (report["tp"], report["fp"], report["fn"]) == (0, 1, 1)


def test_idealized_uncertainty_does_not_claim_target():
    report = match([label(i) for i in range(100)], [decision(i) for i in range(100)], elapsed_s=21600, armed_s=21600)
    assert report["idealized_95pct_recall_lower_all_success"] == pytest.approx(0.97048695)
    assert report["idealized_95pct_zero_fp_upper_per_armed_hour"] == pytest.approx(-math.log(0.05) / 6)
    assert report["session_uncertainty"] == "INSUFFICIENT_SESSION_EVIDENCE"
    assert report["latency_p95_s"] == pytest.approx(0.2)


def test_all_candidates_required_and_tie_order_independent():
    a = candidate_diagnostics([0, 1, 0, 1], [0.2, 0.2, 0.9, 0.9])
    b = candidate_diagnostics([1, 0, 1, 0], [0.9, 0.9, 0.2, 0.2])
    assert a == b
    assert a["roc_auc"] == 0.5
    with pytest.raises(ValueError):
        candidate_diagnostics([1, 1], [0.1, 0.9])
    with pytest.raises(ValueError):
        match([], [], elapsed_s=float("inf"), armed_s=1)
