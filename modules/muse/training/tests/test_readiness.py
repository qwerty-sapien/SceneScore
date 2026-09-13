"""Software-only no-data and split-freeze gates."""
import json

import pytest

from modules.muse.acquisition.tests.helpers import metadata, chunk
from modules.muse.acquisition.tests.test_protocol import protocol
from modules.muse.acquisition.store import Recorder, atomic
from modules.muse.annotation.workflow import label
from modules.muse.training.readiness import freeze_index, readiness_report


def make_session(root, number, role, *, real_marker=True):
    meta = metadata()
    meta["session_id"] = f"fixture-{number}"
    if real_marker:
        meta["provenance"]["source_mode"] = "real_device"
        meta["hardware_verified"] = True
    recorder = Recorder(root / meta["session_id"], meta, explicitly_started=True)
    value = chunk()
    value["session_id"] = meta["session_id"]
    value["provenance"] = meta["provenance"]
    recorder.append(value)
    recorder.close()
    p = protocol() | {"role": role, "refit_id": str(number), "headset_removed_and_refitted": number > 0}
    atomic(recorder.path / "protocol.json", p)
    label(recorder.path, reviewer="fixture-observer", source="independent_observation", evidence_ref="synthetic-test-only",
          epoch="fixture-1", onset_s=.01, end_s=.2, final_blink_s=.15, gesture_count=2,
          intent="deliberate", certainty="uncertain")
    return {"session_id": meta["session_id"], "participant_id": p["participant_id"], "refit_id": p["refit_id"],
            "role": role, "path": meta["session_id"], "consent_ref": p["consent_ref"]}


def test_no_data_has_null_metrics_and_no_artifact(tmp_path):
    result = readiness_report(tmp_path)
    assert result["trained_real_models"] == 0
    assert set(result["metrics"].values()) == {None}
    assert result["model_sha256"] is None
    assert result["matcher"]["status"] == "NOT_LOCKED"
    assert result["closure_floor_ms"] == 500
    assert result["release_status"] == "PIPELINE_TESTED_ONLY"
    assert list(tmp_path.iterdir()) == []


def test_split_freeze_is_exclusive_and_locks_consent_bytes(tmp_path):
    assignments = [make_session(tmp_path, i, role) for i, role in enumerate(("train", "development", "final_test"))]
    target = tmp_path / "split.json"
    freeze_index(tmp_path, assignments, target)
    with pytest.raises(FileExistsError):
        freeze_index(tmp_path, assignments, target)
    index = json.loads(target.read_text())
    from modules.muse.training.pipeline import audit_real
    assert len(audit_real(tmp_path, index)) == 3
    consent = tmp_path / assignments[0]["path"] / "protocol.json"
    consent.write_text(consent.read_text() + " ")
    with pytest.raises(ValueError, match="changed_frozen_protocol"):
        audit_real(tmp_path, index)


def test_split_leakage_and_synthetic_sources_fail_before_output(tmp_path):
    assignments = [make_session(tmp_path, i, role, real_marker=False) for i, role in enumerate(("train", "development", "final_test"))]
    with pytest.raises(ValueError, match="genuine_verified"):
        freeze_index(tmp_path, assignments, tmp_path / "split.json")
    assignments[1]["refit_id"] = assignments[0]["refit_id"]
    with pytest.raises(ValueError, match="refit_split_leakage"):
        freeze_index(tmp_path, assignments, tmp_path / "split.json")
    assert not (tmp_path / "split.json").exists()
