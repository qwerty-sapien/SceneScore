"""New lead stems must remain plan-bound and compatible with strict draft mux checks."""

import json
import hashlib
from pathlib import Path
import wave
import pytest
from tools.mux_performance import verify_export


@pytest.mark.parametrize("fixture_name", ["riff-fixture", "duet-fixture"])
def test_riff_stems_and_sound_design_are_bound(tmp_path, fixture_name):
    b = json.loads(Path(f"packages/audio/tests/{fixture_name}.json").read_text())
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture only: no decoding claimed")
    wav = tmp_path / "fixture.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(bytes(30 * 48000 * 4))

    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    report = {
        k: b[k]
        for k in (
            "sound_design",
            "sound_design_bytes",
            "sound_design_sha256",
            "sound_design_event_bytes",
            "source_events_bytes",
            "plan_bytes",
        )
    }
    stems = ["guitar", *(["piano"] if fixture_name == "duet-fixture" else []), "bass", "brush", "foley"]
    report.update(
        version="performance-export-3",
        status="DRAFT_NOT_APPROVED",
        approval=None,
        video_sha256=sha(video.read_bytes()),
        events=b["events"],
        event_bytes=b["events_bytes"],
        event_hash=b["events_sha256"],
        duration_s=30,
        final_fade_s=0.01,
        stem_layout=stems,
        files=[{"stem": s, "filename": "fixture.wav", "sha256": sha(wav.read_bytes())} for s in ["mix", *stems]],
    )
    path = tmp_path / "report.json"

    def check():
        path.write_text(json.dumps(report))
        return verify_export(path, video)

    assert check()[1] == wav
    report["files"][1]["stem"] = "piano"
    with pytest.raises(ValueError, match="five_aligned"):
        check()
    report["files"][1]["stem"] = "guitar"
    report["sound_design"]["lead"] = "vibraphone"
    with pytest.raises(ValueError, match="unbound_riff"):
        check()
