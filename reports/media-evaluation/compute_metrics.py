#!/usr/bin/env python3
"""Compute the preregistered pairwise bias metrics from six fresh trials."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/media-evaluation"
TRIAL_ROOT = REPORT_ROOT / "trials"
VALID = {"A", "B", "C"}
ALL_CHOICES = VALID | {"NOT_ASSESSABLE"}
TASKS = ("music_pair", "visual_pair", "arranger_pair")
ALPHA_HASH = "f30034eb34f95a65e2e924476b66318133e3b80a84f6444428c01d7bfa50b58d"
BETA_HASH = "6fee6a8b42ba88b91b112d0df7edfc5ff55885b88964e92b6031bec48520afa4"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choices_by_task(trial: dict[str, Any]) -> dict[str, str]:
    values = {item["task_id"]: item["choice"] for item in trial["judgments"]}
    if set(values) != set(TASKS):
        raise ValueError(f'{trial["trial_id"]}: unexpected tasks {sorted(values)}')
    if any(value not in ALL_CHOICES for value in values.values()):
        raise ValueError(f'{trial["trial_id"]}: invalid choice')
    return values


def query_stability(choices: list[str]) -> dict[str, Any]:
    valid = [choice for choice in choices if choice in VALID]
    counts = Counter(choices)
    modal_fraction = max(Counter(valid).values()) / len(valid) if valid else None
    return {
        "choices": choices,
        "counts": dict(sorted(counts.items())),
        "valid_judgments": len(valid),
        "missing_or_not_assessable": len(choices) - len(valid),
        "modal_choice_fraction": modal_fraction,
    }


def classify(original: str, swapped: str) -> str:
    if original not in VALID or swapped not in VALID:
        return "missing_or_not_assessable"
    pair = original + swapped
    if pair in {"AB", "BA", "CC"}:
        return "position_consistent"
    if pair in {"AA", "AC", "CA"}:
        return "primacy"
    if pair in {"BB", "BC", "CB"}:
        return "recency"
    raise ValueError(pair)


def bias_metrics(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in pairs if item["classification"] != "missing_or_not_assessable"]
    category_counts = Counter(item["classification"] for item in pairs)
    choice_pair_counts = Counter(item["choice_pair"] for item in valid)
    n = len(valid)
    consistent = category_counts["position_consistent"]
    primacy = category_counts["primacy"]
    recency = category_counts["recency"]
    inconsistent = primacy + recency
    ipr = primacy / inconsistent if inconsistent else None
    irr = recency / inconsistent if inconsistent else None
    pf_raw = (recency * irr - primacy * ipr) if inconsistent else 0.0
    pf = pf_raw / n if n else None
    return {
        "raw_pairs": pairs,
        "valid_pair_count_N": n,
        "missing_pair_count": len(pairs) - n,
        "choice_pair_counts": dict(sorted(choice_pair_counts.items())),
        "position_consistent_count": consistent,
        "position_inconsistent_count": inconsistent,
        "primacy_counts": {
            "total_pcn": primacy,
            "AA": choice_pair_counts["AA"],
            "AC": choice_pair_counts["AC"],
            "CA": choice_pair_counts["CA"],
        },
        "recency_counts": {
            "total_rcn": recency,
            "BB": choice_pair_counts["BB"],
            "BC": choice_pair_counts["BC"],
            "CB": choice_pair_counts["CB"],
        },
        "consistent_choice_counts": {
            "AB": choice_pair_counts["AB"],
            "BA": choice_pair_counts["BA"],
            "CC": choice_pair_counts["CC"],
        },
        "ties": {
            "consistent_tie_pairs_CC": choice_pair_counts["CC"],
            "choice_pairs_containing_one_tie": sum(
                choice_pair_counts[pair] for pair in ("AC", "CA", "BC", "CB")
            ),
        },
        "ipr": ipr,
        "irr": irr,
        "PF_raw": pf_raw,
        "PF": pf,
        "PC": consistent / n if n else None,
        "formula_notes": {
            "PC": "position-consistent valid original/swapped pairs divided by N",
            "PF_raw": "rcn*irr - pcn*ipr; defined as 0 when there are no inconsistent pairs",
            "PF": "PF_raw/N using preregistered attainable bounds -N and +N",
        },
    }


def unit_findings(sample: dict[str, Any], packet: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {item["path"]: item for item in sample["selected"]}
    music_a = packet["tasks"][0]["candidate_A"]
    music_b = packet["tasks"][0]["candidate_B"]
    scene = packet["tasks"][1]["candidate_A"]
    arranger = packet["tasks"][2]["candidate_A"]
    return [
        {
            **selected["artifacts/music/review-v2/corner_pocket_rag_v1/base/mix.wav"],
            "media_mode": "generated local procedural PCM; manual symbolic plan",
            "objective": {
                "outcome": "evidence-supported pass",
                "facts": music_a["media"],
            },
            "symbolic_music": {
                "outcome": "evidence-supported pass",
                "facts": {
                    "form": "8 bars, 4/4, 120 BPM, C major centre, straight ratio 0.5, explicit harmony and loop boundary",
                    "events": "160 resolved events: 112 notes and 48 unpitched brush events; MIDI pitch 36-82",
                    "phrasing": "36 lead notes, 14 explicit lead rests, call/answer/turnaround roles",
                    "lanes": music_a["symbolic_content"]["separate_control_lanes"],
                    "object_voice": "12 events in one object-motif lane, MIDI pitch 72-79",
                    "groove": "unpitched straight-rag recipe with sweep, tap and chick; no swing application",
                },
                "limit": "Symbolic structure supports the designated straight-rag exception; it does not establish heard coherence or feel.",
            },
            "scene_response": {
                "outcome": "not applicable",
                "reason": "catalogue music unit is not bound to a sampled scene performance",
            },
            "auditory_performance": {
                "outcome": "not assessable",
                "reason": "no usable audio-perception, browser-output, loudspeaker, room, or physical timing modality",
            },
            "provenance": {
                "outcome": "evidence-supported pass",
                "facts": music_a["provenance_claim"],
                "limit": "independent tune-similarity, rights clearance, and cross-platform determinism were not tested",
            },
            "status": "AUDITION_PENDING",
        },
        {
            **selected["artifacts/music/review-v2/velvet_orbit_v1/sparse/mix.wav"],
            "media_mode": "generated local procedural PCM; manual symbolic plan",
            "objective": {
                "outcome": "evidence-supported pass",
                "facts": music_b["media"],
            },
            "symbolic_music": {
                "outcome": "evidence-supported pass",
                "facts": {
                    "form": "8 bars, 4/4, 80 BPM, D minor centre, straight ratio 0.5, explicit extended harmony and loop boundary",
                    "events": "80 resolved events: 56 notes and 24 unpitched brush events; MIDI pitch 38-81",
                    "phrasing": "14 lead notes, 12 explicit lead rests, call/answer/turnaround roles",
                    "lanes": music_b["symbolic_content"]["separate_control_lanes"],
                    "object_voice": "6 events in one object-motif lane, MIDI pitch 74-81",
                    "groove": "unpitched sparse-ballad recipe with sweep, tap and accented swish; no swing application",
                },
                "limit": "Sparse lyrical/ballad evidence is symbolic; heard coherence, bossa colour, swing identity and feel remain unassessed.",
            },
            "supporting_document_accuracy": {
                "outcome": "evidenced defect",
                "evidence": "lead-sheet.md line 6 says 'The straight rag remains straight' although this selected unit uses the sparse-ballad groove and is not the straight-rag composition",
                "impact": "misleading human-readable style description; authoritative JSON remains internally explicit",
            },
            "scene_response": {
                "outcome": "not applicable",
                "reason": "catalogue music unit is not bound to a sampled scene performance",
            },
            "auditory_performance": {
                "outcome": "not assessable",
                "reason": "no usable audio-perception, browser-output, loudspeaker, room, or physical timing modality",
            },
            "provenance": {
                "outcome": "evidence-supported pass",
                "facts": music_b["provenance_claim"],
                "limit": "independent tune-similarity, rights clearance, and cross-platform determinism were not tested",
            },
            "status": "AUDITION_PENDING",
        },
        {
            **selected["artifacts/blender/final-near-miss/10_projectile_tower-near_miss/preview.mp4"],
            "media_mode": "synthetic Blender video and evaluated geometry sidecars",
            "objective": {
                "outcome": "evidence-supported pass",
                "facts": {
                    "video": "H.264, 320x180, 8 fps, 30.0 s, 240/240 frames; ffmpeg decode passed",
                    "geometry": scene["geometry_events"],
                    "validation": "parent validation status PASSED for frame count/duration/hash, evaluated trajectory and continuous near-miss certificate",
                },
            },
            "visible_frame_observations": {
                "outcome": "evidence-supported pass",
                "facts": "four labelled stills and a 12-frame contact sheet show the projectile traversing left-to-right past a stationary segmented tower and separating afterward",
                "limit": "one perspective projection overlaps the tower visually; the positive 0.5 m gap is established by sidecars, not pixels",
            },
            "near_miss_semantics": {
                "outcome": "evidence-supported pass",
                "facts": "three approach, three near-miss and three separation events; minimum reported gap 0.5 m versus 0.00001 m uncertainty; zero contact events and all physical-impact flags false",
                "limit": "scripted analytic sphere/AABB proxy; physical dynamics not simulated",
            },
            "audio_foley": {
                "outcome": "not applicable",
                "reason": "the sampled scene video has no audio stream; geometry supports no contact, but no integrated near-miss soundtrack was evaluated",
            },
            "full_motion_and_physical_sync": {
                "outcome": "not assessable",
                "reason": "decode plus selected frames do not establish full-motion smoothness; there is no audio or physical capture",
            },
            "status": "VISUAL_REVIEW_BOUNDED; FULL_MOTION_NOT_ASSESSED",
        },
        {
            **selected["artifacts/arranger/evaluated-hero-audition/baseline.wav"],
            "media_mode": "draft manual-plan arranger PCM; contact-scene symbolic support",
            "objective": {
                "outcome": "evidence-supported pass",
                "facts": arranger["media"],
            },
            "symbolic_mapping": {
                "outcome": "evidence-supported pass",
                "facts": {
                    "events": "308 resolved events: 200 notes, 96 brushes, 12 Foley schedule records; MIDI pitch 36-73",
                    "lanes": "12 event lanes; 168 events swing-applied once and 140 unswung",
                    "identity": "four persistent motif owners declared; three object voices active in this rendered event set",
                    "motion": "causal world-Z, 0.3 s lookback, 0.02 m/s deadband, prepared signed transitions -2/+2 semitones",
                },
                "limit": "mapping is a draft artistic policy; the fourth declared motif owner is silent under the bounded voice budget",
            },
            "contact_foley": {
                "outcome": "not assessable",
                "reason": "the sampled WAV explicitly excludes Foley; the 12 exact-scene-time schedule records are data, not heard Foley evidence",
            },
            "near_miss": {
                "outcome": "not applicable",
                "reason": "supporting context is the contact-scene candidate, not the sampled near-miss scene",
            },
            "auditory_performance_and_sync": {
                "outcome": "not assessable",
                "reason": "no usable audio-perception, paired video, browser-output, loudspeaker, room, or physical capture modality",
            },
            "approval": {
                "outcome": "not assessable",
                "state": "draft; no human approval object; pending status preserved",
            },
            "status": "AUDITION_PENDING",
        },
    ]


def main() -> None:
    sample = read_json(REPORT_ROOT / "sample.json")
    packet = read_json(REPORT_ROOT / "packet_alpha.json")
    source_checks = read_json(REPORT_ROOT / "source-checks.json")
    if sha256(REPORT_ROOT / "packet_alpha.json") != ALPHA_HASH:
        raise SystemExit("alpha packet changed after trials")
    if sha256(REPORT_ROOT / "packet_beta.json") != BETA_HASH:
        raise SystemExit("beta packet changed after trials")

    trials: dict[str, dict[str, Any]] = {}
    for order, packet_hash in (("alpha", ALPHA_HASH), ("beta", BETA_HASH)):
        for repetition in range(1, 4):
            trial_id = f"{order}-{repetition}"
            trial = read_json(TRIAL_ROOT / f"{trial_id}.json")
            if trial["trial_id"] != trial_id:
                raise ValueError(f"wrong trial id in {trial_id}")
            if trial["requested_model"] != "gpt-5.6-sol" or trial["requested_reasoning"] != "xhigh":
                raise ValueError(f"wrong model request in {trial_id}")
            if trial["packet_sha256"] != packet_hash:
                raise ValueError(f"wrong packet hash in {trial_id}")
            trials[trial_id] = trial

    query_results = []
    modal_values = []
    for task in TASKS:
        for order in ("alpha", "beta"):
            choices = [choices_by_task(trials[f"{order}-{repetition}"])[task] for repetition in range(1, 4)]
            result = {"task_id": task, "order": order, **query_stability(choices)}
            query_results.append(result)
            if result["modal_choice_fraction"] is not None:
                modal_values.append(result["modal_choice_fraction"])
    rs = sum(modal_values) / len(modal_values) if modal_values else None

    pairs = []
    for task in TASKS:
        for repetition in range(1, 4):
            original = choices_by_task(trials[f"alpha-{repetition}"])[task]
            swapped = choices_by_task(trials[f"beta-{repetition}"])[task]
            pairs.append(
                {
                    "task_id": task,
                    "repetition": repetition,
                    "original_choice": original,
                    "swapped_choice": swapped,
                    "choice_pair": original + swapped,
                    "classification": classify(original, swapped),
                }
            )

    per_task = {
        task: bias_metrics([pair for pair in pairs if pair["task_id"] == task]) for task in TASKS
    }
    all_metrics = bias_metrics(pairs)
    substantive = bias_metrics([pair for pair in pairs if pair["task_id"] == "music_pair"])
    controls = bias_metrics([pair for pair in pairs if pair["task_id"] != "music_pair"])
    control_rs_values = [
        item["modal_choice_fraction"]
        for item in query_results
        if item["task_id"] != "music_pair" and item["modal_choice_fraction"] is not None
    ]
    substantive_rs_values = [
        item["modal_choice_fraction"]
        for item in query_results
        if item["task_id"] == "music_pair" and item["modal_choice_fraction"] is not None
    ]

    output = {
        "version": "media-evaluation-metrics-1",
        "status": "COMPLETED_WITH_MODALITY_LIMITS",
        "sampling": {
            "seed": sample["seed"],
            "universe_count": sample["universe_count"],
            "sample_count": sample["sample_count"],
            "fraction": sample["fraction"],
            "stratified": True,
            "self_weighting": False,
            "catalogue_success_rate_inferred": False,
        },
        "source_integrity": {
            "selected_hashes": source_checks["selected_hashes"]["all_match"],
            "protocol_hash": source_checks["protocol_hash"]["match"],
            "indexed_supporting_hashes": source_checks["indexed_supporting_hashes"]["all_match"],
            "indexed_supporting_files_checked": sum(
                group["checked_count"] for group in source_checks["indexed_supporting_hashes"]["groups"]
            ),
            "decoded_media": source_checks["decode_all_pass"],
        },
        "judge_trials": {
            "requested_model": "gpt-5.6-sol",
            "requested_reasoning": "xhigh",
            "fresh_context_count": 6,
            "original_order_contexts": 3,
            "swapped_order_contexts": 3,
            "tasks_per_context": 3,
            "trial_file_count": 6,
            "actual_runtime_model_limit": "the orchestration API accepted the requested model/effort; no separate runtime model fingerprint was exposed",
            "packet_hashes": {"alpha": ALPHA_HASH, "beta": BETA_HASH},
            "query_repetition_results": query_results,
            "missing_or_not_assessable_judgments": sum(
                item["missing_or_not_assessable"] for item in query_results
            ),
        },
        "bias_metrics": {
            "method": "Shi et al. pairwise adaptation; original/swapped trials paired by repetition index",
            "RS_all_queries": rs,
            "all_three_tasks_including_controls": all_metrics,
            "substantive_music_pair": {
                "RS": sum(substantive_rs_values) / len(substantive_rs_values),
                **substantive,
                "interpretation_limit": "technical/symbolic evidence comparison only; no auditory or artistic winner",
            },
            "exact_duplicate_controls": {
                "RS": sum(control_rs_values) / len(control_rs_values),
                **controls,
                "interpretation_limit": "consistency controls only; excluded from substantive media-quality claims",
            },
            "per_task": per_task,
            "tiny_sample_warning": "descriptive only; no unbiasedness, judge validity, music quality, or catalogue-wide certification",
        },
        "unit_findings": unit_findings(sample, packet),
        "open_gates": [
            "human audition and exact-plan approval",
            "full-motion visual review",
            "physical/target browser AV timing and acoustic/display capture",
            "audible contact Foley and integrated near-miss soundtrack review",
            "real Muse data and independently labelled detector evaluation",
        ],
        "release_effect": "None. AUDITION_PENDING and the project formal gate remain open.",
    }
    path = REPORT_ROOT / "metrics.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "RS": rs,
                "PC": all_metrics["PC"],
                "PF": all_metrics["PF"],
                "valid_pairs": all_metrics["valid_pair_count_N"],
                "choice_pair_counts": all_metrics["choice_pair_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
