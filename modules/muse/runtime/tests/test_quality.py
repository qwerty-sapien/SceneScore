from copy import deepcopy
import math

import pytest

from modules.muse.acquisition.tests.helpers import metadata, chunk
from modules.muse.runtime.quality import QualityGate, calibrate_profile, digest


def signal(sequence=0, start=0, count=64, amplitude=10):
    c = chunk(sequence, start, count, quality="unverified")
    c["samples"] = [[amplitude * math.sin(2 * math.pi * 8 * (start + i) / 256),
                     amplitude * math.cos(2 * math.pi * 8 * (start + i) / 256)] for i in range(count)]
    return c


def training_session(meta=None):
    meta = meta or metadata()
    chunks = [signal(i, i * 64) for i in range(8)]
    for c in chunks:
        c["provenance"] = deepcopy(meta["provenance"])
        c["session_id"] = meta["session_id"]
    labels = [{"source": "synthetic_fixture", "reviewer": "software_fixture_not_human"}]
    content = {"metadata": meta, "chunks": chunks, "labels": labels}
    return {**content, "role": "train", "content_sha256": digest(content), "consent_ref": None}


def profile():
    return calibrate_profile(metadata(), [training_session()])


def test_missing_profile_cannot_mark_signal_good():
    gate = QualityGate(metadata(), None)
    assert gate.consume(signal())["state"] == "unverified"
    assert gate.status(100, "anything")["reason"] == "calibrated_quality_profile_missing"


def test_calibration_deterministic_bound_to_training_bytes_and_config():
    p = profile()
    assert p == profile()
    assert p["source_mode"] == "synthetic"
    assert p["calibration"]["window_count"] == 4
    assert p["calibration"]["claim"] == "numeric_signal_only_no_contact_or_accuracy_claim"
    changed = training_session()
    changed["chunks"][0]["samples"][0][0] += 1
    with pytest.raises(ValueError, match="changed_or_ineligible"):
        calibrate_profile(metadata(), [changed])
    for role in ("development", "final_test"):
        changed = training_session()
        changed["role"] = role
        with pytest.raises(ValueError, match="changed_or_ineligible"):
            calibrate_profile(metadata(), [changed])


def test_synthetic_profile_cannot_certify_real_even_if_metadata_claims_verified():
    real = metadata()
    real["hardware_verified"] = True  # negative software fixture, no device used
    real["provenance"]["source_mode"] = "real_device"
    with pytest.raises(ValueError, match="binding_or_hash_mismatch"):
        QualityGate(real, profile())
    s = training_session(real)
    with pytest.raises(ValueError, match="independently_labelled_consented"):
        calibrate_profile(real, [s])


@pytest.mark.parametrize("field", ["device_model", "transport", "sample_rate_hz", "channels", "config_hash"])
def test_exact_hardware_binding_required(field):
    meta = metadata()
    if field == "config_hash":
        meta["provenance"][field] = "b" * 64
    elif field == "sample_rate_hz":
        meta[field] = 250
    elif field == "channels":
        meta[field][0]["unit"] = "mV"
    elif field == "transport":
        meta[field] = "lsl"
    else:
        meta[field] = "different_device"
    with pytest.raises(ValueError):
        QualityGate(meta, profile())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0, True])
def test_invalid_numeric_profile_bounds_rejected(value):
    p = profile()
    p["bounds"]["channels"][0]["abs_max"] = value
    with pytest.raises(ValueError):
        p["sha256"] = digest({k: v for k, v in p.items() if k != "sha256"})
        QualityGate(metadata(), p)


def test_warmup_then_good_means_numeric_checks_only():
    gate = QualityGate(metadata(), profile())
    assert gate.consume(signal())["reason"] == "signal_quality_warmup"
    result = gate.consume(signal(1, 64))
    assert result == {"state": "good", "reason": "calibrated_signal_checks_passed_contact_not_measured"}
    assert gate.status(10.3, "host-1")["state"] == "good"


@pytest.mark.parametrize("problem", ["amplitude", "flatline", "variance", "nonfinite", "upstream_bad"])
def test_causal_sample_fault_clears_window_and_requires_fresh_warmup(problem):
    gate = QualityGate(metadata(), profile())
    c = signal(count=128)
    if problem == "amplitude":
        c["samples"][0][0] = 1000
    elif problem == "flatline":
        c["samples"] = [[0, 0] for _ in c["samples"]]
    elif problem == "variance":
        c = signal(count=128, amplitude=.5)
    elif problem == "nonfinite":
        c["samples"][0][0] = float("nan")
    else:
        c["quality"] = {"state": "bad", "reason": "upstream_failure"}
    assert gate.consume(c)["state"] == "bad"
    gate.reset()
    # Reset deliberately supports midstream sequence/index, never auto-arms.
    assert gate.consume(signal(10, 640))["state"] == "unverified"
    assert gate.consume(signal(11, 704))["state"] == "good"


@pytest.mark.parametrize("problem", ["sequence", "sample_index", "gap", "epoch", "receipt", "internal_gap"])
def test_stream_faults_never_pass_quality(problem):
    gate = QualityGate(metadata(), profile())
    gate.consume(signal())
    c = signal(1, 64)
    if problem == "sequence":
        c["sequence"] = 4
    if problem == "sample_index":
        c["sample_start_index"] += 2
    if problem == "gap":
        c["dropped_samples_before"] = 2
    if problem == "epoch":
        c["device_epoch"] = "new"
    if problem == "receipt":
        c["host_receipt"]["seconds"] += 1
    if problem == "internal_gap":
        c["device_times_s"] = [t + (0 if i < 32 else .1) for i, t in enumerate(c["device_times_s"])]
    assert gate.consume(c)["state"] == "bad"


def test_no_chunk_staleness_disarms_eligibility_without_cross_clock_subtraction():
    gate = QualityGate(metadata(), profile())
    gate.consume(signal(count=128))
    assert gate.status(10.6, "host-1") == {"state": "bad", "reason": "signal_receipt_stale"}
    assert gate.consume(signal(1, 128))["state"] == "unverified"
    assert gate.status(10.5, "other-host-epoch")["state"] == "bad"


def test_causal_chunks_do_not_mutate_raw_input():
    gate = QualityGate(metadata(), profile())
    c = signal(count=128)
    saved = deepcopy(c)
    gate.consume(c)
    assert c == saved


def test_zero_signal_training_cannot_create_profile():
    s = training_session()
    for c in s["chunks"]:
        c["samples"] = [[0, 0] for _ in c["samples"]]
    s["content_sha256"] = digest({k: s[k] for k in ("metadata", "chunks", "labels")})
    with pytest.raises(ValueError, match="nonflat_training"):
        calibrate_profile(metadata(), [s])
