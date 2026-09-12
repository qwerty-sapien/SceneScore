#!/usr/bin/env python3
"""Verify the frozen sample and hash-indexed supporting evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/media-evaluation"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check_index(folder: Path, entries: dict[str, str], label: str) -> dict[str, Any]:
    checks = []
    for relative, expected in sorted(entries.items()):
        path = folder / relative
        actual = digest(path) if path.is_file() else None
        checks.append(
            {
                "relative_path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "match": actual == expected,
            }
        )
    return {
        "label": label,
        "checked_count": len(checks),
        "all_match": all(item["match"] for item in checks),
        "checks": checks,
    }


def probe(path: Path) -> dict[str, Any]:
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
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return {
        "command": command,
        "returncode": result.returncode,
        "stderr": result.stderr,
        "probe": json.loads(result.stdout) if result.returncode == 0 else None,
    }


def decode(path: Path) -> dict[str, Any]:
    command = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-f", "null", "-"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return {"command": command, "returncode": result.returncode, "stderr": result.stderr}


def main() -> None:
    sample = read_json(REPORT_ROOT / "sample.json")
    selected = []
    for item in sample["selected"]:
        actual = digest(ROOT / item["path"])
        selected.append({**item, "actual_sha256": actual, "match": actual == item["sha256"]})
    protocol_actual = digest(REPORT_ROOT / "PROTOCOL.md")

    music_dirs = [
        ROOT / "artifacts/music/review-v2/corner_pocket_rag_v1/base",
        ROOT / "artifacts/music/review-v2/velvet_orbit_v1/sparse",
    ]
    supporting = [
        check_index(folder, read_json(folder / "manifest.json")["files"], f"music-unit-{index}")
        for index, folder in enumerate(music_dirs, start=1)
    ]
    scene_dir = ROOT / "artifacts/blender/final-near-miss/10_projectile_tower-near_miss"
    supporting.append(
        check_index(scene_dir, read_json(scene_dir / "bundle_hashes.json")["files"], "scene-bundle")
    )

    arranger_dir = ROOT / "artifacts/arranger/evaluated-hero-audition"
    arranger_support = [
        {
            "relative_path": str(path.relative_to(ROOT)),
            "observed_sha256": digest(path),
            "status": "OBSERVED_ONLY_NO_FROZEN_SUPPORT_INDEX",
        }
        for path in (
            arranger_dir / "input.json",
            arranger_dir / "plan.json",
            arranger_dir / "baseline-events.json",
            arranger_dir / "foley-events.json",
        )
    ]

    selected_paths = [ROOT / item["path"] for item in sample["selected"]]
    probes = [{"path": str(path.relative_to(ROOT)), **probe(path)} for path in selected_paths]
    decodes = [{"path": str(path.relative_to(ROOT)), **decode(path)} for path in selected_paths]
    report = {
        "version": "media-source-checks-1",
        "selected_hashes": {
            "count": len(selected),
            "all_match": all(item["match"] for item in selected),
            "checks": selected,
        },
        "protocol_hash": {
            "expected_sha256": sample["protocol_sha256"],
            "actual_sha256": protocol_actual,
            "match": protocol_actual == sample["protocol_sha256"],
        },
        "indexed_supporting_hashes": {
            "all_match": all(group["all_match"] for group in supporting),
            "groups": supporting,
        },
        "unindexed_arranger_support": arranger_support,
        "ffprobe": probes,
        "ffmpeg_decode": decodes,
        "decode_all_pass": all(item["returncode"] == 0 for item in decodes),
        "limits": [
            "Hash agreement establishes byte identity, not semantic or perceptual quality.",
            "ffprobe and ffmpeg decode success do not establish hearing, visual smoothness, or physical AV synchronization.",
            "Arranger supporting JSON has no sampled frozen support index; observed hashes are provenance only.",
        ],
    }
    output = REPORT_ROOT / "source-checks.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not (
        report["selected_hashes"]["all_match"]
        and report["protocol_hash"]["match"]
        and report["indexed_supporting_hashes"]["all_match"]
        and report["decode_all_pass"]
    ):
        raise SystemExit("source verification failed")
    print(
        json.dumps(
            {
                "selected_hashes": "PASS",
                "protocol_hash": "PASS",
                "indexed_supporting_hashes": "PASS",
                "decoded_media": "PASS",
                "supporting_files_checked": sum(group["checked_count"] for group in supporting),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
