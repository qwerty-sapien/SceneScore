"""Calibrated causal numeric signal checks, never contact/impedance inference.

Profiles are computed from exact frozen training-session bytes. A profile is an
exploratory software gate, not an accuracy, medical or device-contact certificate.
"""
from collections import deque
from copy import deepcopy
import hashlib
import math
import statistics

from modules.muse.acquisition.store import encoded
from scenescore.contracts import validate

FORMAT = "scenescore.signal-quality/1"
DEFAULT_CONFIG = {"window_s": .5, "max_receipt_gap_s": .5,
                  "max_sample_gap_periods": 1.5, "amplitude_margin": 1.5,
                  "variance_lower_factor": .1, "variance_upper_factor": 4.0,
                  "flatline_range_factor": .01}
INDEPENDENT = {"independent_observation", "consented_local_video", "independent_review"}


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def hardware_binding(metadata):
    validate(metadata)
    if metadata["kind"] != "AcquisitionMetadata":
        raise ValueError("acquisition_metadata_required")
    return {name: deepcopy(metadata[name]) for name in
            ("device_model", "transport", "sample_rate_hz", "channels", "hardware_verified")} | {
                "acquisition_config_sha256": metadata["provenance"]["config_hash"]}


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _config(config, rate):
    if set(config) != set(DEFAULT_CONFIG) or not all(_positive(v) for v in config.values()):
        raise ValueError("finite_quality_calibration_config_required")
    if (not 2 <= math.ceil(config["window_s"] * rate) <= 8192
            or not .01 <= config["max_receipt_gap_s"] <= 10
            or not 1 < config["max_sample_gap_periods"] <= 10
            or not 1 <= config["amplitude_margin"] <= 10
            or not 0 < config["variance_lower_factor"] < 1
            or not 1 < config["variance_upper_factor"] <= 100
            or not 0 < config["flatline_range_factor"] < 1):
        raise ValueError("quality_calibration_config_bounds")


def validate_profile(metadata, profile):
    binding = hardware_binding(metadata)
    if set(profile) != {"format", "hardware", "hardware_sha256", "source_mode", "calibration", "bounds", "sha256"}:
        raise ValueError("invalid_quality_profile_fields")
    if (profile["format"] != FORMAT or profile["hardware"] != binding
            or profile["hardware_sha256"] != digest(binding)
            or profile["sha256"] != digest({k: v for k, v in profile.items() if k != "sha256"})):
        raise ValueError("quality_profile_binding_or_hash_mismatch")
    if (profile["source_mode"] not in {"synthetic", "real_device"}
            or profile["source_mode"] != metadata["provenance"]["source_mode"]):
        raise ValueError("quality_profile_provenance_mismatch")
    if profile["source_mode"] == "real_device" and not metadata["hardware_verified"]:
        raise ValueError("verified_real_hardware_required")
    rate = metadata["sample_rate_hz"]
    calibration = profile["calibration"]
    if (set(calibration) != {"method", "config", "sessions", "window_count", "claim"}
            or calibration["method"] != "train-window-extrema-v1"
            or calibration["claim"] != "numeric_signal_only_no_contact_or_accuracy_claim"
            or not isinstance(calibration["window_count"], int) or calibration["window_count"] < 2):
        raise ValueError("invalid_quality_calibration")
    _config(calibration["config"], rate)
    sessions = calibration["sessions"]
    if not isinstance(sessions, list) or not 1 <= len(sessions) <= 100:
        raise ValueError("quality_training_sessions_required")
    if len({s["session_id"] for s in sessions}) != len(sessions):
        raise ValueError("duplicate_quality_training_session")
    for session in sessions:
        if (set(session) != {"session_id", "role", "source_mode", "content_sha256", "metadata_sha256", "labels_sha256", "consent_ref", "label_sources", "reviewers"}
                or not session["session_id"] or session["role"] != "train"
                or session["source_mode"] != profile["source_mode"]
                or not all(_hash(session[key]) for key in ("content_sha256", "metadata_sha256", "labels_sha256"))):
            raise ValueError("invalid_quality_training_provenance")
        if profile["source_mode"] == "real_device" and (
                not session["consent_ref"] or not session["label_sources"] or not session["reviewers"]
                or not set(session["label_sources"]).issubset(INDEPENDENT)
                or any(not reviewer for reviewer in session["reviewers"])):
            raise ValueError("independently_labelled_consented_training_required")
    bounds = profile["bounds"]
    if set(bounds) != {"window_s", "max_receipt_gap_s", "max_sample_gap_s", "channels"}:
        raise ValueError("invalid_quality_bounds")
    config = calibration["config"]
    if (bounds["window_s"] != config["window_s"] or bounds["max_receipt_gap_s"] != config["max_receipt_gap_s"]
            or bounds["max_sample_gap_s"] != config["max_sample_gap_periods"] / rate):
        raise ValueError("quality_bounds_config_mismatch")
    enabled = [c for c in metadata["channels"] if c["enabled"]]
    if not enabled or len(enabled) > 32 or len(bounds["channels"]) != len(enabled):
        raise ValueError("bounded_enabled_channels_required")
    for c, b in zip(enabled, bounds["channels"]):
        if (set(b) != {"name", "unit", "abs_max", "variance_min", "variance_max", "flatline_peak_to_peak_max"}
                or c["name"] != b["name"] or c["unit"] != b["unit"]
                or not all(_positive(b[k]) for k in ("abs_max", "variance_min", "variance_max", "flatline_peak_to_peak_max"))
                or not b["variance_min"] < b["variance_max"]
                or not b["flatline_peak_to_peak_max"] < 2 * b["abs_max"]):
            raise ValueError("finite_channel_quality_bounds_required")
    return profile


def calibrate_profile(metadata, sessions, *, config=None):
    """Fit training-only numeric bounds; labels establish provenance, not features.

    Each session supplies metadata/chunks/labels, role='train', content_sha256
    binding those three values, and a consent_ref for real recordings. The
    training command must first audit the complete train/development/test split.
    This function never reads files or silently selects a final-test session.
    """
    config = dict(DEFAULT_CONFIG if config is None else config)
    binding, rate = hardware_binding(metadata), metadata["sample_rate_hz"]
    _config(config, rate)
    mode = metadata["provenance"]["source_mode"]
    if mode not in {"synthetic", "real_device"} or not 1 <= len(sessions) <= 100:
        raise ValueError("eligible_quality_training_sessions_required")
    enabled = [i for i, c in enumerate(metadata["channels"]) if c["enabled"]]
    if not 1 <= len(enabled) <= 32:
        raise ValueError("bounded_enabled_channels_required")
    n = math.ceil(rate * config["window_s"])
    amplitudes, variances, ranges = ([[] for _ in enabled] for _ in range(3))
    evidence, total, window_count = [], 0, 0
    for session in sessions:
        meta, chunks, labels = session["metadata"], session["chunks"], session["labels"]
        if (session["role"] != "train" or hardware_binding(meta) != binding
                or meta["provenance"]["source_mode"] != mode or not labels
                or digest({"metadata": meta, "chunks": chunks, "labels": labels}) != session["content_sha256"]):
            raise ValueError("changed_or_ineligible_quality_training_session")
        label_sources = sorted({label.get("source", "") for label in labels})
        reviewers = sorted({label.get("reviewer", "") for label in labels})
        if mode == "real_device" and (not meta["hardware_verified"] or not session.get("consent_ref")
                or not set(label_sources).issubset(INDEPENDENT) or any(not r for r in reviewers)):
            raise ValueError("independently_labelled_consented_training_required")
        evidence.append({"session_id": meta["session_id"], "role": "train", "source_mode": mode,
            "content_sha256": session["content_sha256"], "metadata_sha256": digest(meta),
            "labels_sha256": digest(labels), "consent_ref": session.get("consent_ref"),
            "label_sources": label_sources, "reviewers": reviewers})
        rows, previous = [], None
        for chunk in chunks:
            validate(chunk)
            if (chunk["kind"] != "EEGChunk" or chunk["session_id"] != meta["session_id"]
                    or chunk["channels"] != meta["channels"] or chunk["sample_rate_hz"] != rate
                    or chunk["provenance"]["source_mode"] != mode or not chunk["samples"]):
                raise ValueError("quality_training_chunk_mismatch")
            total += len(chunk["samples"])
            if total > 1_000_000:
                raise ValueError("quality_training_sample_budget")
            gap = _discontinuity(previous, chunk, config["max_sample_gap_periods"] / rate,
                                 config["max_receipt_gap_s"])
            if gap or chunk["quality"]["state"] == "bad":
                rows.clear()
                previous = _endpoint(chunk)
                continue
            previous = _endpoint(chunk)
            for row in chunk["samples"]:
                rows.append(row)
                if len(rows) == n:
                    for j, i in enumerate(enabled):
                        values = [r[i] for r in rows]
                        amplitudes[j].append(max(abs(v) for v in values))
                        variances[j].append(statistics.pvariance(values))
                        ranges[j].append(max(values) - min(values))
                    window_count += 1
                    rows.clear()
    if window_count < 2 or any(min(v) <= 0 for v in variances) or any(min(v) <= 0 for v in ranges):
        raise ValueError("nonflat_training_signal_windows_required")
    bounds = {"window_s": config["window_s"], "max_receipt_gap_s": config["max_receipt_gap_s"],
              "max_sample_gap_s": config["max_sample_gap_periods"] / rate,
              "channels": [{"name": metadata["channels"][i]["name"], "unit": metadata["channels"][i]["unit"],
                "abs_max": max(amplitudes[j]) * config["amplitude_margin"],
                "variance_min": min(variances[j]) * config["variance_lower_factor"],
                "variance_max": max(variances[j]) * config["variance_upper_factor"],
                "flatline_peak_to_peak_max": min(ranges[j]) * config["flatline_range_factor"]}
                for j, i in enumerate(enabled)]}
    profile = {"format": FORMAT, "hardware": binding, "hardware_sha256": digest(binding),
               "source_mode": mode, "calibration": {"method": "train-window-extrema-v1", "config": config,
               "sessions": evidence, "window_count": window_count,
               "claim": "numeric_signal_only_no_contact_or_accuracy_claim"}, "bounds": bounds}
    profile["sha256"] = digest(profile)
    validate_profile(metadata, profile)
    return profile


def _endpoint(chunk):
    return {"sequence": chunk["sequence"], "end_index": chunk["sample_start_index"] + len(chunk["samples"]),
            "device_s": chunk["device_times_s"][-1], "device_epoch": chunk["device_epoch"],
            "receipt": deepcopy(chunk["host_receipt"])}


def _discontinuity(previous, chunk, max_sample_gap, max_receipt_gap):
    times = chunk["device_times_s"]
    if chunk["dropped_samples_before"] or any(b - a > max_sample_gap for a, b in zip(times, times[1:])):
        return "signal_dropout"
    if previous is None:
        return None  # an explicit reset may resume at any valid sequence/index
    if previous["device_epoch"] != chunk["device_epoch"] or previous["receipt"]["epoch"] != chunk["host_receipt"]["epoch"]:
        return "signal_epoch_changed"
    if (chunk["sequence"] != previous["sequence"] + 1 or chunk["sample_start_index"] != previous["end_index"]
            or not 0 < times[0] - previous["device_s"] <= max_sample_gap):
        return "signal_dropout_or_nonmonotonic"
    if not 0 <= chunk["host_receipt"]["seconds"] - previous["receipt"]["seconds"] <= max_receipt_gap:
        return "signal_receipt_stale"
    return None


class QualityGate:
    def __init__(self, metadata, profile=None):
        self.metadata = deepcopy(metadata)
        hardware_binding(metadata)
        self.profile = deepcopy(validate_profile(metadata, profile)) if profile is not None else None
        self.indices = [i for i, c in enumerate(metadata["channels"]) if c["enabled"]]
        self.n = math.ceil(profile["bounds"]["window_s"] * metadata["sample_rate_hz"]) if profile else 0
        self.reset()

    def reset(self):
        self.windows = [deque(maxlen=self.n) for _ in self.indices]
        self.previous = None
        self.quality = {"state": "unverified", "reason": "signal_quality_warmup" if self.profile
                        else "calibrated_quality_profile_missing"}

    def _bad(self, reason):
        for window in self.windows:
            window.clear()
        self.quality = {"state": "bad", "reason": reason}
        return deepcopy(self.quality)

    def consume(self, chunk):
        if self.profile is None:
            return deepcopy(self.quality)
        try:
            validate(chunk)
            if (chunk["kind"] != "EEGChunk" or not 0 < len(chunk["samples"]) <= 4096
                    or any(chunk[k] != self.metadata[k] for k in ("session_id", "channels", "sample_rate_hz"))
                    or chunk["provenance"]["source_mode"] != self.metadata["provenance"]["source_mode"]):
                return self._bad("signal_metadata_or_provenance_mismatch")
        except (ValueError, KeyError, TypeError):
            return self._bad("invalid_or_nonfinite_signal_chunk")
        bounds = self.profile["bounds"]
        reason = _discontinuity(self.previous, chunk, bounds["max_sample_gap_s"], bounds["max_receipt_gap_s"])
        self.previous = _endpoint(chunk)
        if reason:
            return self._bad(reason)
        if chunk["quality"]["state"] == "bad":
            return self._bad("upstream_signal_quality_bad")
        for row in chunk["samples"]:
            for index, window, bound in zip(self.indices, self.windows, bounds["channels"]):
                value = row[index]
                if abs(value) > bound["abs_max"]:
                    return self._bad("signal_amplitude_outside_calibration")
                window.append(value)
                if len(window) == self.n:
                    if max(window) - min(window) <= bound["flatline_peak_to_peak_max"]:
                        return self._bad("signal_flatline")
                    variance = statistics.pvariance(window)
                    if not bound["variance_min"] <= variance <= bound["variance_max"]:
                        return self._bad("signal_variance_outside_calibration")
        self.quality = ({"state": "good", "reason": "calibrated_signal_checks_passed_contact_not_measured"}
                        if all(len(window) == self.n for window in self.windows)
                        else {"state": "unverified", "reason": "signal_quality_warmup"})
        return deepcopy(self.quality)

    def status(self, now_host_s, host_epoch):
        if self.profile is None or self.previous is None:
            return deepcopy(self.quality)
        receipt = self.previous["receipt"]
        if (not isinstance(now_host_s, (int, float)) or not math.isfinite(now_host_s)
                or host_epoch != receipt["epoch"]
                or not 0 <= now_host_s - receipt["seconds"] <= self.profile["bounds"]["max_receipt_gap_s"]):
            return self._bad("signal_receipt_stale")
        return deepcopy(self.quality)
