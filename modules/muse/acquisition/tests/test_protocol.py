"""Synthetic transport and protocol fixtures; no participant or hardware evidence."""
import builtins
import json
import sys
from types import SimpleNamespace

import pytest

from modules.muse.acquisition.diagnostics import diagnose_transport
from modules.muse.acquisition.protocol import collect_session, validate_protocol
from modules.muse.acquisition.store import Recorder, manifest
from modules.muse.acquisition.tests.helpers import metadata, chunk
from modules.muse.acquisition.tests.test_live import fake_lsl, live_metadata
from modules.muse.annotation.workflow import confirm, cues
from modules.muse.baseline.replay import replay_session


def protocol():
    return {"format": "scenescore.collection-protocol/1", "participant_id": "synthetic-test-person",
            "refit_id": "synthetic-refit-1", "role": "train", "consent_ref": "synthetic-consent-fixture",
            "consent_words": "Synthetic test fixture only; no person was recorded",
            "retention_until": "2099-01-01", "recorded_at_utc": "2026-09-13T00:00:00Z",
            "consent": {key: True for key in ("frontal_eeg_and_timestamps", "local_storage_only",
                                             "retention_understood", "stop_and_delete_anytime")},
            "mode": "natural_activity", "headset_removed_and_refitted": False, "seed": 1}


def test_diagnostic_missing_dependency_is_precise_and_reads_no_samples(monkeypatch):
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "pylsl":
            raise ImportError("test missing pylsl")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    result = diagnose_transport()
    assert result["code"] == "OPTIONAL_DEPENDENCY_UNAVAILABLE"
    assert result["samples_read"] == 0
    assert result["verified_sample_rate_hz"] is None
    assert not result["recording"]


def test_no_stream_diagnostic_does_not_construct_inlet(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylsl", SimpleNamespace(resolve_streams=lambda **kwargs: []))
    assert diagnose_transport()["code"] == "NO_ADVERTISED_LSL_STREAM"
    with pytest.raises(ValueError):
        diagnose_transport(timeout_s=100)


def test_protocol_requires_real_explicit_consent_not_truthy_strings():
    value = protocol()
    value["consent"]["stop_and_delete_anytime"] = "yes"
    with pytest.raises(ValueError, match="consent_required"):
        validate_protocol(value)


def test_fake_collection_preserves_consent_refit_and_exposure(tmp_path, monkeypatch):
    stop, closed = fake_lsl(monkeypatch)
    messages = []
    result = collect_session(tmp_path / "s", live_metadata(), protocol=protocol(), source_id="fixture",
                             seconds=20, explicitly_started=True, stop=stop, report=messages.append)
    assert closed == [True]
    assert result["summary"]["samples"] == 2
    assert result["summary"]["sampled_exposure_s"] == 2 / 256
    assert result["summary"]["armed_exposure_s"] == 0
    persisted = json.loads((tmp_path / "s" / "protocol.json").read_text())
    assert persisted["role"] == "train"
    assert not persisted["publication_consent"]
    assert all("raw_channels" not in value for value in messages if isinstance(value, dict))


def test_confirmation_is_forbidden_while_recording(tmp_path):
    recorder = Recorder(tmp_path / "s", metadata(), explicitly_started=True)
    recorder.append(chunk())
    cue = cues(recorder.path, mode="randomized_instructed", count=1)[0]
    try:
        with pytest.raises(ValueError, match="recording_stops"):
            confirm(recorder.path, cue["id"], performed="performed", confirmation_s=100)
    finally:
        recorder.close()


def test_deterministic_replay_and_fault_does_not_rearm(tmp_path):
    recorder = Recorder(tmp_path / "s", metadata(), explicitly_started=True)
    for value in [chunk(count=257), chunk(1, 257, count=256), chunk(2, 513, quality="bad"), chunk(3, 577, count=256)]:
        recorder.append(value)
    recorder.close()
    a = replay_session(recorder.path, arm_after_s=1)
    assert a == replay_session(recorder.path, arm_after_s=1)
    assert a["recording_source_mode"] == "synthetic"
    assert a["faults"] == [{"sequence": 2, "reason": "bad_quality", "rearm_required": True}]
    assert not a["armed_at_end"]
    assert manifest(recorder.path)["metadata"]["provenance"]["source_mode"] == "synthetic"


def test_advertised_metadata_keeps_unknown_fields_null_and_never_opens_inlet(monkeypatch):
    class Channel:
        def child_value(self, name):
            return ""
        def next_sibling(self):
            return self
    class Description:
        def child(self, name):
            return Channel() if name == "channel" else self
    info = SimpleNamespace(channel_count=lambda: 2, desc=Description, nominal_srate=lambda: 123,
                           source_id=lambda: "test-source", name=lambda: "test-stream", type=lambda: "EEG")
    monkeypatch.setitem(sys.modules, "pylsl", SimpleNamespace(resolve_streams=lambda **kwargs: [info]))
    result = diagnose_transport()
    assert result["status"] == "METADATA_OBSERVED_UNVERIFIED"
    assert result["streams"][0]["advertised_sample_rate_hz"] == 123
    assert result["streams"][0]["channels"] == [{"index": 0, "name": None, "unit": None}, {"index": 1, "name": None, "unit": None}]
    assert result["verified_sample_rate_hz"] is None
    assert result["firmware"] is None
