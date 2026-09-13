"""Clock-safe ladder summaries. All values are scheduled/software observations."""

import math
from .events import quantile


def intervals(envelope):
    t = envelope["timing"]
    pairs = {
        "final_blink_to_decision_ms": ("t0_final_blink_s", "t1_decision_s"),
        "request_to_receipt_ms": ("t3_request_s", "t4_received_s"),
        "receipt_to_scheduled_ack_ms": ("t4_received_s", "t5_ack_onset_s"),
        "scheduled_ack_to_tonic_arrival_ms": ("t5_ack_onset_s", "t6_boundary_s"),
    }
    out, reasons = {}, {}
    for name, (a, b) in pairs.items():
        if t[a] is None or t[b] is None:
            out[name] = None
            reasons[name] = "missing_clock_domain_stamp"
        elif any(not math.isfinite(t[k]) for k in (a, b)) or t[b] < t[a]:
            out[name] = None
            reasons[name] = "invalid_or_reversed_stamp"
        else:
            out[name] = 1000 * (t[b] - t[a])
    # There is intentionally no t2-t1 subtraction: their domains differ.
    out["dispatch_after_decision_ms"] = None
    reasons["dispatch_after_decision_ms"] = "device_to_host_mapping_not_supplied"
    return {"version": "muse-latency-intervals-1", "intervals_ms": out,
            "unavailable_reasons": reasons, "acoustic_latency_ms": None,
            "acoustic_unavailable_reason": "no_loopback_or_microphone_measurement"}


def summarize(envelopes):
    rows = [intervals(envelope) for envelope in envelopes]
    names = list(rows[0]["intervals_ms"]) if rows else []
    return {"version": "muse-latency-summary-1", "sample_count": len(rows),
            "percentile_method": "sorted[ceil(q*(n-1))]",
            "intervals": {name: {"n": len(values), "p50_ms": quantile(values, .5),
                                 "p95_ms": quantile(values, .95)}
                          for name in names
                          for values in [[row["intervals_ms"][name] for row in rows
                                          if row["intervals_ms"][name] is not None]]},
            "release_status": "PIPELINE_TESTED_ONLY"}
