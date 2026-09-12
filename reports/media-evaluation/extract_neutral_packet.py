#!/usr/bin/env python3
"""Build frozen, identity-neutral evidence packets for the sampled media review.

This script reads only the four preregistered units and their supporting data. It
does not render, transform, approve, or modify any source media. The emitted
packets deliberately omit source paths, candidate titles/variants, content
hashes, prior evaluation conclusions, and audition labels. Hashes and the
private packet-to-source mapping are retained in coordinator provenance only.
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import shutil
import subprocess
import wave
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/media-evaluation"
ARTIFACT_ROOT = ROOT / "artifacts/media-evaluation"
SAMPLE_PATH = REPORT_ROOT / "sample.json"
PROTOCOL_PATH = REPORT_ROOT / "PROTOCOL.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=format_name,duration,size,bit_rate:"
            "stream=codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,"
            "sample_rate,channels,duration,nb_frames"
        ),
        "-of",
        "json",
        str(path),
    ]
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)


def wav_measure(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        compression = wav.getcomptype()
        raw = wav.readframes(frames)
    if sample_width != 2 or compression != "NONE":
        raise ValueError(f"expected uncompressed PCM16 WAV: {path}")
    samples = array.array("h")
    samples.frombytes(raw)
    if samples.itemsize != 2:
        raise ValueError("unexpected host integer width")
    scale = 32768.0
    peak = max((abs(value) for value in samples), default=0) / scale
    rms = math.sqrt(sum(value * value for value in samples) / max(len(samples), 1)) / scale
    return {
        "codec": "PCM signed 16-bit little-endian",
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "frames": frames,
        "duration_s": frames / sample_rate,
        "sample_peak": peak,
        "rms": rms,
        "clipped_samples": sum(abs(value) >= 32767 for value in samples),
        "nonzero_samples": sum(value != 0 for value in samples),
        "first_sample": samples[0] if samples else None,
        "last_sample": samples[-1] if samples else None,
        "decode_status": "PASS",
    }


def music_evidence(folder: Path) -> dict[str, Any]:
    manifest = read_json(folder / "manifest.json")
    score = read_json(folder / "score.json")
    composition = read_json(folder / "composition.json")
    brush = read_json(folder / "brush.json")
    events = read_json(folder / "events.json")
    notes = composition["notes"]
    note_events = [event for event in events if event["event_type"] == "note"]
    object_events = [event for event in note_events if event.get("object_id") is not None]
    lanes = Counter(event["lane_id"] for event in events)
    articulations = Counter(event["articulation"] for event in events)
    phrase_roles = Counter(item["role"] for item in score["lanes"]["phrasing"]["phrases"])
    harmony = [
        {
            "start_tick": chord["start_tick"],
            "duration_ticks": chord["duration_ticks"],
            "root_pitch_class": chord["root_pc"],
            "quality": chord["quality"],
            "intervals_semitones": chord["intervals_semitones"],
        }
        for chord in composition["harmony"]
    ]
    return {
        "modalities": ["parsed symbolic JSON", "decoded PCM statistics"],
        "media": wav_measure(folder / "mix.wav"),
        "form": {
            "ppq": composition["ppq"],
            "meter": composition["meter"],
            "tempo_map": composition["tempo_map"],
            "key_map": composition["key_map"],
            "length_ticks": composition["length_ticks"],
            "form_duration_s": manifest["form_duration_s"],
            "release_tail_s": manifest["tail_s"],
            "bar_count": composition["length_ticks"]
            / (composition["ppq"] * composition["meter"][0]),
            "harmony": harmony,
            "loop_boundary_ticks": score["loop"],
        },
        "symbolic_content": {
            "lead_note_count": len(notes),
            "lead_pitch_range": [min(note["midi_pitch"] for note in notes), max(note["midi_pitch"] for note in notes)],
            "lead_unique_pitch_count": len({note["midi_pitch"] for note in notes}),
            "lead_rest_count": len(score["lanes"]["phrasing"]["lead_rests"]),
            "phrase_roles": dict(sorted(phrase_roles.items())),
            "resolved_event_count": len(events),
            "resolved_note_count": len(note_events),
            "resolved_brush_count": len(events) - len(note_events),
            "resolved_pitch_range": [
                min(event["midi_pitch"] for event in note_events),
                max(event["midi_pitch"] for event in note_events),
            ],
            "lane_event_counts": dict(sorted(lanes.items())),
            "articulation_counts": dict(sorted(articulations.items())),
            "swing_application_counts": dict(
                sorted(Counter(str(event["swing_application_count"]) for event in events).items())
            ),
            "separate_control_lanes": sorted(score["lanes"].keys()),
        },
        "groove": {
            "meter": brush["meter"],
            "ppq": brush["ppq"],
            "length_ticks": brush["length_ticks"],
            "pitched": brush["pitched"],
            "technique_counts": dict(sorted(Counter(item["technique"] for item in brush["events"]).items())),
            "swingable_recipe_events": sum(bool(item["swingable"]) for item in brush["events"]),
            "max_humanize_ms": brush["max_humanize_ms"],
            "max_velocity_delta": brush["max_velocity_delta"],
        },
        "persistent_voice_evidence": {
            "object_event_count": len(object_events),
            "object_lane_count": len({event["lane_id"] for event in object_events}),
            "object_pitch_range": [
                min(event["midi_pitch"] for event in object_events),
                max(event["midi_pitch"] for event in object_events),
            ],
            "scope_limit": "one unit; persistence across key changes or multiple loops is not established",
        },
        "provenance_claim": {
            "source_mode": manifest["generation_mode"],
            "renderer": manifest["renderer"],
            "seed_present": isinstance(manifest.get("seed"), int),
            "normalization": manifest["normalization"],
            "asset_statement": "project-authored procedural output; no third-party samples; distribution terms unspecified",
            "claim_limit": "metadata was inspected; independent tune-similarity or rights verification was not performed",
        },
        "criterion_limits": {
            "auditory": "NOT_ASSESSABLE: no audio-perception tool was used",
            "aesthetic": "NOT_ASSESSABLE from symbolic and PCM statistics",
            "style": "Only written meter, harmony, rhythm, density, rests and groove recipe are assessable",
            "performance": "No browser, loudspeaker, room, or physical synchronization evidence",
        },
    }


def scene_evidence(folder: Path) -> dict[str, Any]:
    manifest = read_json(folder / "manifest.json")
    qa = read_json(folder / "qa.json")
    summary = read_json(folder / "summary.json")
    interactions = [json.loads(line) for line in (folder / "interactions.jsonl").read_text().splitlines() if line]
    event_counts = Counter(event["event_type"] for event in interactions)
    gaps = [event["surface_gap_m"] for event in interactions]
    uncertainties = [event["uncertainty_m"] for event in interactions]
    return {
        "modalities": ["decoded video container", "four labelled still frames", "parsed geometry/event sidecars"],
        "video": ffprobe(folder / "preview.mp4"),
        "scene": {
            "duration_s": manifest["duration_s"],
            "fps": f'{manifest["fps"]}/{manifest["fps_base"]}',
            "expected_frames": qa["expected_frame_count"],
            "rendered_frames": qa["frame_count"],
            "object_count": len(manifest["objects"]),
            "stable_sonic_identity_count": len({item["sonic_identity_id"] for item in manifest["objects"]}),
            "units": manifest["units"],
            "up_axis": manifest["up_axis"],
            "handedness": manifest["handedness"],
            "matrix_layout": manifest["matrix_layout"],
            "quaternion_order": manifest["quaternion_order"],
        },
        "geometry_events": {
            "count": len(interactions),
            "event_type_counts": dict(sorted(event_counts.items())),
            "pair_count": len({event["pair_id"] for event in interactions}),
            "minimum_reported_gap_m": min(gaps),
            "maximum_uncertainty_m": max(uncertainties),
            "all_gaps_exceed_uncertainty": all(gap > uncertainty for gap, uncertainty in zip(gaps, uncertainties)),
            "all_physical_impact_false": all(not event["physical_impact"] for event in interactions),
            "contact_event_count": sum(event["event_type"].startswith("contact") for event in interactions),
            "approach_speeds_m_s": [
                event["relative_normal_speed_m_s"] for event in interactions if event["event_type"] == "approach"
            ],
            "separation_speeds_m_s": [
                event["relative_normal_speed_m_s"] for event in interactions if event["event_type"] == "separation"
            ],
            "method": sorted({event["method"] for event in interactions}),
            "geometry_method": sorted({item["geometry_method"] for item in summary["event_details"]}),
            "physical_dynamics": sorted({item["physical_dynamics"] for item in summary["event_details"]}),
        },
        "still_observation_scope": {
            "frames": ["still_1.png", "still_2.png", "still_3.png", "still_4.png"],
            "meaning": "selected start, approach, closest-event, and ending observations; labels visible",
        },
        "provenance_claim": {
            "source_mode": manifest["provenance"]["source_mode"],
            "tool_version": manifest["provenance"]["tool_version"],
            "seed_present": isinstance(manifest["provenance"].get("seed"), int),
            "interaction_method": "scripted with analytic sphere/AABB proxy",
            "physical_dynamics": "not simulated",
        },
        "criterion_limits": {
            "full_motion": "NOT_ASSESSABLE from four stills; decode success does not establish smoothness",
            "sound": "NOT_APPLICABLE: sampled scene unit has no audio stream",
            "foley_absence": "No audio stream means no contact Foley is present; this does not evaluate an integrated near-miss soundtrack",
            "physical_sync": "NOT_ASSESSABLE: no physical capture or audio stream",
            "visual_qa": "four frames permit bounded visible observations only",
        },
    }


def arranger_evidence(folder: Path) -> dict[str, Any]:
    events = read_json(folder / "baseline-events.json")
    foley = read_json(folder / "foley-events.json")
    plan = read_json(folder / "plan.json")
    note_events = [event for event in events if event["event_type"] == "note"]
    return {
        "modalities": ["decoded PCM statistics", "parsed draft plan and symbolic event schedules"],
        "media": wav_measure(folder / "baseline.wav"),
        "symbolic_content": {
            "resolved_event_count": len(events),
            "event_type_counts": dict(sorted(Counter(event["event_type"] for event in events).items())),
            "resolved_pitch_range": [
                min(event["midi_pitch"] for event in note_events),
                max(event["midi_pitch"] for event in note_events),
            ],
            "object_voice_count": len({event["object_id"] for event in events if event.get("object_id")}),
            "swing_application_counts": dict(
                sorted(Counter(str(event["swing_application_count"]) for event in events).items())
            ),
            "separate_event_lanes": len({event["lane_id"] for event in events}),
        },
        "scene_mapping": {
            "draft_review_status": plan["review_status"],
            "mapping_features": sorted(item["feature"] for item in plan["mappings"]),
            "persistent_motif_owner_count": len(plan["motif_owners"]),
            "motion_axis": plan["motion_policy"]["axis"],
            "motion_lookback_s": plan["motion_policy"]["lookback_s"],
            "motion_deadband_m_s": plan["motion_policy"]["deadband_m_s"],
            "signed_transition_options": sorted({item["signed_semitones"] for item in plan["transitions"]}),
            "foley_schedule_count": len(foley),
            "foley_scene_times_s": sorted({event["scene_time_s"] for event in foley}),
            "critical_limit": "the sampled WAV excludes Foley; its separate schedule is supporting data only",
        },
        "provenance_claim": {
            "source_mode": plan["provenance"]["source_mode"],
            "seed_present": isinstance(plan["provenance"].get("seed"), int),
            "review_state": "draft; no approval object was supplied or inferred",
        },
        "criterion_limits": {
            "auditory": "NOT_ASSESSABLE: no audio-perception tool was used",
            "contact_foley": "NOT_ASSESSABLE in this WAV because Foley was explicitly excluded",
            "near_miss": "NOT_APPLICABLE to this candidate's contact-scene context",
            "physical_sync": "NOT_ASSESSABLE: no physical capture or paired video",
            "human_approval": "ABSENT; must remain pending",
        },
    }


def packet(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "packet_version": "neutral-media-judge-1",
        "instructions": {
            "role": "independent pairwise evidence judge",
            "choice": "Return A, B, C (tie), or NOT_ASSESSABLE for each task.",
            "basis": (
                "Compare only criteria supported by the supplied evidence. Prefer C when evidence is materially equal. "
                "Use NOT_ASSESSABLE when the requested comparison depends on a missing modality."
            ),
            "prohibitions": [
                "Do not infer hearing from PCM statistics or note names.",
                "Do not infer full-motion smoothness or physical AV synchronization from still frames or decode metadata.",
                "Do not infer human approval, rights clearance, originality, or aesthetic quality beyond the explicit evidence.",
                "Do not inspect repository files outside this packet and its neutral still paths.",
            ],
            "response_fields": [
                "task_id",
                "choice",
                "underlying_evidence_preference (A/B/C/NOT_ASSESSABLE)",
                "evidence",
                "criterion_outcomes",
                "modality_limits",
            ],
        },
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    sample = read_json(SAMPLE_PATH)
    selected = {item["path"]: item["sha256"] for item in sample["selected"]}
    verified = []
    for relative, expected in selected.items():
        actual = sha256(ROOT / relative)
        verified.append({"path": relative, "expected": expected, "actual": actual, "match": actual == expected})
    protocol_actual = sha256(PROTOCOL_PATH)
    all_match = all(item["match"] for item in verified) and protocol_actual == sample["protocol_sha256"]
    if not all_match:
        raise SystemExit("frozen sample/protocol hash verification failed")
    if args.check_only:
        print(json.dumps({"all_match": True, "selected": verified, "protocol_sha256": protocol_actual}, indent=2))
        return

    music_one_path = ROOT / "artifacts/music/review-v2/corner_pocket_rag_v1/base"
    music_two_path = ROOT / "artifacts/music/review-v2/velvet_orbit_v1/sparse"
    scene_path = ROOT / "artifacts/blender/final-near-miss/10_projectile_tower-near_miss"
    arranger_path = ROOT / "artifacts/arranger/evaluated-hero-audition"

    music_one = music_evidence(music_one_path)
    music_two = music_evidence(music_two_path)
    scene = scene_evidence(scene_path)
    arranger = arranger_evidence(arranger_path)

    still_root = ARTIFACT_ROOT / "neutral/stills"
    still_root.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(("start.png", "approach.png", "event.png", "ending.png"), start=1):
        shutil.copyfile(scene_path / name, still_root / f"still_{index}.png")

    common_rubric = {
        "music_pair": (
            "Which candidate has stronger evidence on shared technical and symbolic requirements: decodable non-silent PCM with headroom; "
            "editable coherent form/harmony; explicit independent control lanes and rests; style evidence appropriate to its written form; "
            "and bounded persistent object-voice evidence? Exclude auditory quality, aesthetic preference, and unverified originality."
        ),
        "visual_pair": (
            "Which candidate has stronger evidence on identical technical/geometry/visible-still criteria: video decode/duration/frame count, "
            "positive-gap approach-near-miss-separation semantics, stable identities, honest provenance, and the four neutral stills? "
        ),
        "arranger_pair": (
            "Which candidate has stronger evidence on identical PCM and symbolic schedule criteria: decodable non-silent PCM with headroom, "
            "explicit lanes/object voices/signed mapping, and honest draft provenance? Auditory quality, Foley sound, physical sync, and approval are absent. "
        ),
    }
    alpha_tasks = [
        {"task_id": "music_pair", "rubric": common_rubric["music_pair"], "candidate_A": music_one, "candidate_B": music_two},
        {"task_id": "visual_pair", "rubric": common_rubric["visual_pair"], "candidate_A": scene, "candidate_B": scene},
        {"task_id": "arranger_pair", "rubric": common_rubric["arranger_pair"], "candidate_A": arranger, "candidate_B": arranger},
    ]
    beta_tasks = [
        {"task_id": "music_pair", "rubric": common_rubric["music_pair"], "candidate_A": music_two, "candidate_B": music_one},
        {"task_id": "visual_pair", "rubric": common_rubric["visual_pair"], "candidate_A": scene, "candidate_B": scene},
        {"task_id": "arranger_pair", "rubric": common_rubric["arranger_pair"], "candidate_A": arranger, "candidate_B": arranger},
    ]

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "packet_alpha.json").write_text(json.dumps(packet(alpha_tasks), indent=2) + "\n", encoding="utf-8")
    (REPORT_ROOT / "packet_beta.json").write_text(json.dumps(packet(beta_tasks), indent=2) + "\n", encoding="utf-8")
    mapping = {
        "version": "neutral-media-judge-mapping-1",
        "private_to_coordinator": True,
        "packet_alpha": {
            "music_pair": {"A": str(music_one_path.relative_to(ROOT)), "B": str(music_two_path.relative_to(ROOT))},
            "visual_pair": {"A": str(scene_path.relative_to(ROOT)), "B": str(scene_path.relative_to(ROOT)), "control": "exact_duplicate"},
            "arranger_pair": {"A": str(arranger_path.relative_to(ROOT) / "baseline.wav"), "B": str(arranger_path.relative_to(ROOT) / "baseline.wav"), "control": "exact_duplicate"},
        },
        "packet_beta": {
            "music_pair": {"A": str(music_two_path.relative_to(ROOT)), "B": str(music_one_path.relative_to(ROOT))},
            "visual_pair": {"A": str(scene_path.relative_to(ROOT)), "B": str(scene_path.relative_to(ROOT)), "control": "exact_duplicate"},
            "arranger_pair": {"A": str(arranger_path.relative_to(ROOT) / "baseline.wav"), "B": str(arranger_path.relative_to(ROOT) / "baseline.wav"), "control": "exact_duplicate"},
        },
    }
    provenance = {
        "version": "media-evaluation-provenance-1",
        "sample_seed": sample["seed"],
        "sample_fraction": sample["fraction"],
        "hash_verification": {"all_match": True, "selected": verified, "protocol_sha256": protocol_actual},
        "neutral_packets": {
            "alpha_sha256": sha256(REPORT_ROOT / "packet_alpha.json"),
            "beta_sha256": sha256(REPORT_ROOT / "packet_beta.json"),
            "mapping": mapping,
            "metadata_limits": [
                "Source paths, content hashes, titles, variation labels, prior reports, and audition labels were removed from judge packets.",
                "Durations, tempo, harmony, density, event counts, scene structure, and renderer facts may still permit identity inference.",
                "Duplicate controls are intentionally identical and can be recognized as such from their evidence.",
                "Packet statistics are coordinator-extracted evidence, not independent recomputation by each judge.",
            ],
        },
    }
    (REPORT_ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_match": True, "packet_alpha": provenance["neutral_packets"]["alpha_sha256"], "packet_beta": provenance["neutral_packets"]["beta_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
