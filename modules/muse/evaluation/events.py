"""Frozen chronological one-to-one matching; abstention/cooldown labels stay in denominator."""

from dataclasses import asdict, dataclass
import math
import statistics


@dataclass(frozen=True)
class Matcher:
    tolerance_s: float = 0.75
    version: str = "event-matcher-1"

    def __post_init__(self):
        if not 0.01 <= self.tolerance_s <= 2:
            raise ValueError("matcher_window_range")


def quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(q * (len(ordered) - 1))]


def match(labels, decisions, *, elapsed_s, armed_s, config=Matcher(), data_mode="synthetic", suppression_s=None):
    if not math.isfinite(elapsed_s) or not math.isfinite(armed_s) or not 0 < elapsed_s or not 0 <= armed_s <= elapsed_s:
        raise ValueError("exposure_range")
    if len({label["id"] for label in labels}) != len(labels) or len({d["id"] for d in decisions}) != len(decisions):
        raise ValueError("duplicate_record_id")
    if any(not 0 <= v["final_blink_s"] <= elapsed_s for v in labels + decisions):
        raise ValueError("event_outside_exposure")
    if any(d["decision_s"] < d["final_blink_s"] or not math.isfinite(d["decision_s"]) for d in decisions):
        raise ValueError("noncausal_decision")
    truth = [
        label for label in labels if label["intent"] == "deliberate" and label["gesture_count"] == 2 and label["certainty"] == "verified"
    ]
    used = set()
    pairs = []
    fp = []
    latencies = []
    for d in sorted(decisions, key=lambda d: (d["decision_s"], d["id"])):
        eligible = [
            label
            for label in truth
            if label["id"] not in used
            and label["session_id"] == d["session_id"]
            and label["epoch"] == d["epoch"]
            and d["decision_s"] >= label["final_blink_s"]
            and abs(label["final_blink_s"] - d["final_blink_s"]) <= config.tolerance_s
            and d["gesture_count"] == 2
        ]
        if eligible:
            label = min(eligible, key=lambda label: (abs(label["final_blink_s"] - d["final_blink_s"]), label["final_blink_s"], label["id"]))
            used.add(label["id"])
            pairs.append({"label_id": label["id"], "decision_id": d["id"]})
            latencies.append(d["decision_s"] - label["final_blink_s"])
        else:
            fp.append(d["id"])
    fn = [label["id"] for label in truth if label["id"] not in used]
    tp = len(pairs)
    recall = tp / len(truth) if truth else None
    precision = tp / len(decisions) if decisions else None
    eligible_truth = [label for label in truth if label.get("eligible", False)]
    per_session = {}
    for session in sorted({label["session_id"] for label in labels} | {d["session_id"] for d in decisions}):
        session_truth = [label for label in truth if label["session_id"] == session]
        per_session[session] = {
            "opportunities": len(session_truth),
            "matched": sum(label["id"] in used for label in session_truth),
            "fp": sum(d["id"] in fp for d in decisions if d["session_id"] == session),
        }
    confusion = {}
    for d in decisions:
        close = [
            label
            for label in labels
            if label["session_id"] == d["session_id"]
            and label["epoch"] == d["epoch"]
            and d["decision_s"] >= label["final_blink_s"]
            and abs(label["final_blink_s"] - d["final_blink_s"]) <= config.tolerance_s
        ]
        if close:
            label = min(close, key=lambda label: abs(label["final_blink_s"] - d["final_blink_s"]))
            key = f"{label['intent']}_{label['gesture_count']}_to_{d['gesture_count']}"
            confusion[key] = confusion.get(key, 0) + 1
    lower = 0.05 ** (1 / len(truth)) if truth and not fn else None
    return {
        "format": "scenescore.event-evaluation/1",
        "data_mode": data_mode,
        "status": "PIPELINE_TESTED_ONLY" if data_mode == "synthetic" else "REAL_PROVENANCE_NOT_VERIFIED",
        "matcher": asdict(config),
        "tp": tp,
        "fp": len(fp),
        "fn": len(fn),
        "recall_all": recall,
        "precision": precision,
        "f1": 2 * tp / (2 * tp + len(fp) + len(fn)) if truth or decisions else None,
        "eligible_recall": sum(label["id"] in used for label in eligible_truth) / len(eligible_truth)
        if eligible_truth
        else None,
        "eligible_denominator": len(eligible_truth),
        "all_opportunities": len(truth),
        "elapsed_hours": elapsed_s / 3600,
        "armed_hours": armed_s / 3600,
        "availability": armed_s / elapsed_s,
        "false_per_armed_hour": len(fp) / (armed_s / 3600) if armed_s else None,
        "false_per_elapsed_hour": len(fp) / (elapsed_s / 3600),
        "latency_median_s": statistics.median(latencies) if latencies else None,
        "latency_p95_s": quantile(latencies, 0.95),
        "bar_wait": "reported_by_audio_transport_separately",
        "pairs": pairs,
        "false_decisions": fp,
        "missed_labels": fn,
        "confusion": confusion,
        "per_session": per_session,
        "ambiguous_labels": sum(label["certainty"] != "verified" or label["intent"] == "ambiguous" for label in labels),
        "suppression_seconds": suppression_s or {},
        "idealized_95pct_recall_lower_all_success": lower,
        "idealized_95pct_zero_fp_upper_per_armed_hour": -math.log(0.05) / (armed_s / 3600)
        if not fp and armed_s
        else None,
        "uncertainty_assumptions": "independent Bernoulli opportunities / stationary Poisson; dependent sessions require additional session-level analysis",
        "nonzero_error_interval": "NOT_ESTIMATED; no statistical support claim",
        "session_uncertainty": "INSUFFICIENT_SESSION_EVIDENCE",
        "candidate_diagnostics": "Separate full candidate stream required; accepted positives alone cannot yield AUC",
    }


def candidate_diagnostics(labels, scores):
    if len(labels) != len(scores) or not labels or set(labels) != {0, 1} or any(not math.isfinite(v) for v in scores):
        raise ValueError("both_classes_full_candidate_stream_required")
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    auc = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))
    # Group equal scores; AP must not depend on order of tied input rows.
    count = correct = 0
    ap = 0
    for threshold in sorted(set(scores), reverse=True):
        group = [y for y, s in zip(labels, scores) if s == threshold]
        count += len(group)
        correct += sum(group)
        ap += sum(group) / len(pos) * correct / count
    return {
        "roc_auc": auc,
        "average_precision": ap,
        "unit": "all candidate windows; excludes upstream missed candidates",
        "denominator": len(labels),
        "candidate_coverage": "report separately against all independent gesture labels",
    }
