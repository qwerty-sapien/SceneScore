#!/usr/bin/env python3
"""Analytic controls for the Muse pack's grammar cases and latency ladder.

Stdlib only. Run from the pack root: python3 examples/check_pack_examples.py
Writes examples/reference_check_results.json.

This is a REFERENCE grammar used to check the pack's own declared cases. It is not the
detector, establishes no EEG accuracy, and must not be copied into the runtime in place
of modules/muse/baseline/causal.py::Grammar.
"""
import copy, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
CASES = json.loads((HERE / "gesture_grammar_cases.json").read_text())
LADDER = json.loads((HERE / "latency_ladder.json").read_text())
FAILS = []


def check(name, condition, detail=""):
    if not condition:
        FAILS.append(f"{name}: {detail}")
    return condition


def run_grammar(case, cfg):
    """Closure-before-commitment reference. Returns the number of accepted doubles."""
    fault = case.get("fault") or {}
    fault_at = fault.get("dropout_at_s", fault.get("quality_loss_at_s"))
    valid = [(on, d) for on, d in case["blinks_s"]
             if on >= cfg["warmup_s"] and cfg["min_duration_s"] <= d <= cfg["max_duration_s"]]
    trains, current = [], []
    for on, d in valid:
        if current and cfg["min_separation_s"] <= on - current[-1][0] <= cfg["max_gap_s"]:
            current.append((on, d))
        else:
            if current:
                trains.append(current)
            current = [(on, d)]
    if current:
        trains.append(current)
    accepted, cooldown_until = 0, -1e9
    for train in trains:
        if len(train) != 2:                      # singles and triples alike emit nothing
            continue
        first, second = train[0][0], train[1][0]
        if fault_at is not None and first <= fault_at <= second + cfg["max_gap_s"]:
            continue                             # partial state cleared, re-arm required
        if first < cooldown_until:
            continue
        decision = second + cfg["max_gap_s"]     # closure delay is real and disclosed
        accepted += 1
        cooldown_until = decision + cfg["cooldown_s"]
    return accepted


EXPECTED = {"accept": 1, "accept_twice": 2, "accept_once": 1, "reject": 0}


def validate_ladder(l):
    bad, names = [], {s["name"] for s in l["stamps"]}
    for needed in ("t0_final_blink_s", "t1_decision_s", "t4_received_s", "t5_ack_onset_s", "t6_boundary_s"):
        if needed not in names:
            bad.append(f"missing stamp {needed}")
    gates = {b["interval"]: b["gate"] for b in l["budgets"]}
    if "t5 - t4" not in gates or "300" not in gates["t5 - t4"]:
        bad.append("the 300 ms responsiveness gate must be stated on t5 - t4 and nowhere else")
    if "t6 - t5" not in gates or "unbounded" not in gates["t6 - t5"]:
        bad.append("the musical boundary wait must be declared unbounded")
    for b in l["budgets"]:
        if b["interval"] != "t5 - t4" and "300" in str(b["gate"]):
            bad.append(f"300 ms gate wrongly attached to {b['interval']}")
    clocks = {s["name"]: s["clock"] for s in l["stamps"]}
    if clocks.get("t1_decision_s") == clocks.get("t4_received_s"):
        bad.append("device and audio clock domains must stay distinct")
    return bad


def main():
    cfg = CASES["config_under_test"]
    check("config order", cfg["min_separation_s"] < cfg["max_gap_s"], "separation bounds out of order")
    check("config order", cfg["min_duration_s"] < cfg["max_duration_s"], "duration bounds out of order")
    floor_ms = cfg["max_gap_s"] * 1000
    check("closure fits the 750 ms gate", floor_ms < 750,
          f"closure floor {floor_ms:.0f} ms leaves no processing headroom")

    rows = []
    for case in CASES["positive_controls"] + CASES["negative_controls"]:
        got = run_grammar(case, cfg)
        want = EXPECTED[case["expect"]]
        ok = got == want
        check(f"case {case['id']}", ok, f"expected {want} accepted, got {got}")
        rows.append({"id": case["id"], "expect": case["expect"], "accepted": got, "passed": ok})

    triple = next(c for c in CASES["negative_controls"] if c["id"] == "N2")
    check("prefix safety", run_grammar(triple, cfg) == 0, "a triple emitted a double")

    ladder_bad = validate_ladder(LADDER)
    check("latency_ladder", not ladder_bad, "; ".join(ladder_bad))

    negatives = []
    for label, mutate in [
        ("300 ms gate moved onto the boundary wait",
         lambda l: l["budgets"].__setitem__(4, {"interval": "t6 - t5", "gate": "<= 300 ms", "source": "x"})),
        ("responsiveness gate deleted",
         lambda l: l["budgets"].__setitem__(3, {"interval": "t5 - t4", "gate": "best effort", "source": "x"})),
        ("decision stamp removed", lambda l: l["stamps"].pop(1)),
        ("clock domains collapsed", lambda l: [s.update(clock="audio") for s in l["stamps"]]),
    ]:
        doc = copy.deepcopy(LADDER)
        mutate(doc)
        rejected = bool(validate_ladder(doc))
        check(f"negative::{label}", rejected, "mutation was not detected")
        negatives.append({"mutation": label, "rejected": rejected})

    for label, mutate in [
        ("max_gap_s raised past the latency gate", lambda c: c.update(max_gap_s=0.8)),
        ("separation bounds inverted", lambda c: c.update(min_separation_s=0.9)),
    ]:
        doc = copy.deepcopy(cfg)
        mutate(doc)
        broken = not (doc["min_separation_s"] < doc["max_gap_s"]) or doc["max_gap_s"] * 1000 >= 750
        check(f"negative::{label}", broken, "mutation was not detected")
        negatives.append({"mutation": label, "rejected": broken})

    results = {
        "status": "PASSED" if not FAILS else "FAILED",
        "closure_floor_ms": floor_ms,
        "processing_headroom_ms": 750 - floor_ms,
        "grammar_cases": rows,
        "latency_ladder_violations": ladder_bad,
        "negative_controls": negatives,
        "failures": FAILS,
    }
    (HERE / "reference_check_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: results[k] for k in
                      ("status", "closure_floor_ms", "processing_headroom_ms", "failures")}, indent=2))
    print(f"grammar cases passed: {sum(1 for r in rows if r['passed'])}/{len(rows)}")
    print(f"negative controls rejected: {sum(1 for n in negatives if n['rejected'])}/{len(negatives)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
