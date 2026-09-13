#!/usr/bin/env python3
"""Analytic positive and negative controls for the music pack's reference artifacts.

Stdlib only. Run from the pack root: python3 examples/check_pack_examples.py
Writes examples/reference_check_results.json. This validates the pack's own data,
not the SceneScore implementation; it certifies nothing about audio.
"""
import copy, itertools, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
TABLE = json.loads((HERE / "transition_table.json").read_text())
TAXON = json.loads((HERE / "motion_event_taxonomy.json").read_text())
FAILS = []


def check(name, condition, detail=""):
    if not condition:
        FAILS.append(f"{name}: {detail}")
    return condition


def pc_distance(a, b):
    d = abs(a - b) % 12
    return min(d, 12 - d)


def voice_leads(a_pcs, b_pcs, limit):
    """Some 3-voice upper structure moves from a to b within `limit` semitones per voice."""
    for ca in itertools.combinations(sorted(a_pcs), 3):
        for cb in itertools.combinations(sorted(b_pcs), 3):
            for perm in itertools.permutations(cb):
                if all(pc_distance(x, y) <= limit for x, y in zip(ca, perm)):
                    return True
    return False


def validate_table(t):
    """Return a list of violation strings. Empty means the table is internally sound."""
    bad, seen = [], set()
    inv = t["invariants"]
    if inv["gain_db_delta"] != 0:
        bad.append("gain_db_delta must be 0")
    if inv["articulation_change"] or inv["expression_preset_change"]:
        bad.append("modulation may not change articulation or expression preset")
    if set(inv["lanes_affected"]) & set(inv["lanes_untouched"]):
        bad.append("lane sets overlap")
    if inv["acknowledgement"]["max_ms_from_accepted_control"] > 300:
        bad.append("acknowledgement budget exceeds 300 ms")
    for r in t["resolved"]:
        key = (r["gesture_id"], r["from_pc"], r["signed_semitones"], r["lead_bars"])
        if key in seen:
            bad.append(f"duplicate lookup key {key}")
        seen.add(key)
        if r["to_pc"] != (r["from_pc"] + r["signed_semitones"]) % 12:
            bad.append(f"to_pc mismatch for {key}")
        arrival = r["slots"][-1]
        if arrival["offset_ticks"] != 0 or arrival["root_pc"] != r["to_pc"]:
            bad.append(f"arrival slot not on the new tonic downbeat for {key}")
        if r["lead_ticks"] != -r["slots"][0]["offset_ticks"] or r["lead_ticks"] <= 0:
            bad.append(f"lead_ticks inconsistent for {key}")
        for s in r["slots"]:
            expected = sorted({(s["root_pc"] + i) % 12 for i in t["qualities"][s["quality"]]})
            if s["pitch_classes"] != expected:
                bad.append(f"pitch classes do not match {s['quality']} for {key}")
            if s["offset_ticks"] % (t["bar_ticks"] // 2):
                bad.append(f"slot off the half-bar grid for {key}")
        limit = inv["voice_leading"]["max_semitones_per_voice"]
        for a, b in zip(r["slots"], r["slots"][1:]):
            if not voice_leads(a["pitch_classes"], b["pitch_classes"], limit):
                bad.append(f"no voice leading within {limit} semitones for {key}")
    for tier_name, tier in t["tiers"].items():
        for delta in tier["eligible_signed_semitones"]:
            for pc in range(12):
                hits = [r for r in t["resolved"]
                        if r["signed_semitones"] == delta and r["from_pc"] == pc
                        and r["gesture_id"] in tier["gesture_by_lead_bars"].values()]
                if not hits:
                    bad.append(f"{tier_name} has no entry for pc {pc} delta {delta}")
        if tier["audition_required"] and not tier["enable_flag"]:
            bad.append(f"{tier_name} requires audition but declares no enable flag")
        if not tier["audition_required"] and tier["enable_flag"]:
            bad.append(f"{tier_name} is default but gated behind a flag")
    return bad


def validate_taxonomy(x):
    bad = []
    vocab = set(x["lane_vocabulary"]["existing"]) | set(x["lane_vocabulary"]["added_by_this_pack"])
    types = [e["event_type"] for e in x["events"]]
    if len(set(types)) != len(types):
        bad.append("duplicate event_type")
    for e in x["events"]:
        for lane, rng in e["lanes"].items():
            if lane not in vocab:
                bad.append(f"{e['event_type']} uses unknown lane {lane}")
            if len(rng) != 2 or rng[0] > rng[1]:
                bad.append(f"{e['event_type']} lane {lane} range is not ordered")
    nm = next(e for e in x["events"] if e["event_type"] == "near_miss")
    if nm["accent"]:
        bad.append("near_miss must not accent")
    if "percussive accent" not in nm.get("forbidden", []):
        bad.append("near_miss must forbid a percussive accent")
    rb = next((e for e in x["events"] if e["event_type"] == "asymmetric_rebound"), None)
    if rb is None:
        bad.append("asymmetric_rebound is missing")
    else:
        if rb["fields"]["mass_inferred"] or rb["fields"]["restitution_claimed"]:
            bad.append("asymmetric_rebound may not claim mass or restitution")
        if rb["defaults"]["rebound_min_area_ratio"] <= 1:
            bad.append("area ratio threshold must exceed 1")
    return bad


NEGATIVES = [
    ("table", "wrong to_pc", lambda t: t["resolved"][0].update(to_pc=(t["resolved"][0]["to_pc"] + 1) % 12)),
    ("table", "slot quality mismatch", lambda t: t["resolved"][0]["slots"][0]["pitch_classes"].__setitem__(0, 11)),
    ("table", "arrival not on tonic", lambda t: t["resolved"][0]["slots"][-1].update(offset_ticks=480)),
    ("table", "gain changed", lambda t: t["invariants"].update(gain_db_delta=-3)),
    ("table", "articulation changed", lambda t: t["invariants"].update(articulation_change=True)),
    ("table", "lane sets overlap", lambda t: t["invariants"]["lanes_untouched"].append("bass")),
    ("table", "acknowledgement budget blown", lambda t: t["invariants"]["acknowledgement"].update(max_ms_from_accepted_control=900)),
    ("table", "duplicate lookup key", lambda t: t["resolved"].append(copy.deepcopy(t["resolved"][0]))),
    ("table", "default tier flag-gated", lambda t: t["tiers"]["contract_default"].update(enable_flag="X")),
    ("table", "voice leading broken", lambda t: t["resolved"][0]["slots"][0].update(pitch_classes=[1, 2, 3, 4], quality="dom7", root_pc=1)),
    ("taxonomy", "near miss accents", lambda x: next(e for e in x["events"] if e["event_type"] == "near_miss").update(accent=True)),
    ("taxonomy", "rebound claims mass", lambda x: next(e for e in x["events"] if e["event_type"] == "asymmetric_rebound")["fields"].update(mass_inferred=True)),
    ("taxonomy", "unknown lane", lambda x: x["events"][0]["lanes"].update(loudness=[0, 1])),
    ("taxonomy", "reversed lane range", lambda x: x["events"][0]["lanes"].update(ornament=[1.0, 0.0])),
]


def main():
    results = {"positive_controls": {}, "negative_controls": []}
    tbl_bad, tax_bad = validate_table(TABLE), validate_taxonomy(TAXON)
    check("transition_table", not tbl_bad, "; ".join(tbl_bad[:6]))
    check("motion_event_taxonomy", not tax_bad, "; ".join(tax_bad[:6]))
    results["positive_controls"] = {
        "transition_table_entries": len(TABLE["resolved"]),
        "transition_table_violations": tbl_bad,
        "motion_event_types": len(TAXON["events"]),
        "motion_taxonomy_violations": tax_bad,
    }
    for target, label, mutate in NEGATIVES:
        doc = copy.deepcopy(TABLE if target == "table" else TAXON)
        mutate(doc)
        found = validate_table(doc) if target == "table" else validate_taxonomy(doc)
        rejected = bool(found)
        check(f"negative::{label}", rejected, "mutation was not detected")
        results["negative_controls"].append(
            {"target": target, "mutation": label, "rejected": rejected})
    results["status"] = "PASSED" if not FAILS else "FAILED"
    results["failures"] = FAILS
    (HERE / "reference_check_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in results.items() if k != "negative_controls"}, indent=2))
    print(f"negative controls rejected: "
          f"{sum(1 for n in results['negative_controls'] if n['rejected'])}/{len(NEGATIVES)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
