"""Prepare a separate guitar/vibraphone audition catalogue; preserve all source bundles."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

from modules.arranger.collision_riffs import arrange
from modules.arranger.core import encoded
from modules.music.render import _track, _varlen


def write_midi(path, b):
    """Editable General MIDI approximation; exact synthesis/scene timing stays in JSON."""
    tracks = [_track([(0, 0, b"\xff\x51\x03" + (625000).to_bytes(3, "big"))], 46080)]
    instrument = b["sound_design"]["lead"]
    for lane, channel, program in [
        ("lead", 0, 24 if instrument == "guitar" else 11),
        ("bass", 1, 32),
        ("brush", 9, 0),
        ("foley", 2, 115),
    ]:
        name = (instrument if lane == "lead" else lane).encode()
        data = [(0, 0, b"\xff\x03" + _varlen(len(name)) + name), (0, 1, bytes([0xC0 + channel, program]))]
        for e in b["events"]:
            part = (
                "foley"
                if e["event_type"] == "foley"
                else "brush"
                if e["event_type"] == "brush"
                else "bass"
                if "bass" in e["instrument_id"]
                else "lead"
            )
            if part != lane:
                continue
            pitch = e["midi_pitch"] if e["midi_pitch"] is not None else 38 if lane == "brush" else 60
            start = round(e["resolved_time_s"] * 1536)
            end = max(start + 1, round((e["resolved_time_s"] + e["duration_s"]) * 1536))
            data += [
                (start, 3, bytes([0x90 + channel, pitch, e["velocity"]])),
                (end, 2, bytes([0x80 + channel, pitch, 0])),
            ]
        tracks.append(_track(data, 46080))
    path.write_bytes(b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), 960) + b"".join(tracks))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("apps/web/public/studio"))
    p.add_argument("--out", type=Path, default=Path("apps/web/public/riff-studio"))
    p.add_argument("--scores", type=Path, default=Path("artifacts/collision-riffs/scores"))
    args = p.parse_args()
    if args.out.resolve() == args.source.resolve():
        raise ValueError("source_and_output_must_differ")
    args.out.mkdir(parents=True, exist_ok=True)
    args.scores.mkdir(parents=True, exist_ok=True)
    source = json.loads((args.source / "catalog.json").read_text())
    entries = []
    legacy = []
    for row in source["entries"]:
        raw = (args.source / row["url"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("source_bundle_hash_mismatch")
        b = json.loads(raw)
        video = (args.source / b["video"]).read_bytes()
        if hashlib.sha256(video).hexdigest() != b["video_sha256"]:
            raise ValueError("source_video_hash_mismatch")
        shutil.copyfile(args.source / b["video"], args.out / b["video"])
        shutil.copyfile(args.source / row["url"], args.out / row["url"])
        legacy.append({**row, "arrangement": "piano"})
        for lead in ("guitar", "vibraphone"):
            candidate = arrange(b, lead)
            payload = encoded(candidate)
            filename = candidate["id"] + ".json"
            (args.out / filename).write_bytes(payload)
            entries.append(
                {
                    **row,
                    "id": candidate["id"],
                    "url": filename,
                    "arrangement": lead,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
            if row["groove"] == "brush_swing_light_v1":
                score = args.scores / candidate["id"]
                score.mkdir(exist_ok=True)
                for name, content in [
                    ("composition.json", candidate["composition"]),
                    ("events.json", candidate["events"]),
                    ("sound-design.json", candidate["sound_design"]),
                    ("plan.json", json.loads(candidate["plan_bytes"])),
                ]:
                    (score / name).write_bytes(encoded(content))
                write_midi(score / "score.mid", candidate)
    (args.out / "catalog.json").write_bytes(encoded({"version": "studio-catalog-1", "entries": entries + legacy}))
    print(
        json.dumps(
            {"entries": len(entries) + len(legacy), "new_drafts": len(entries), "out": str(args.out), "approval": None}
        )
    )


if __name__ == "__main__":
    main()
