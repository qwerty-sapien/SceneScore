"""Optional exact-ID LSL receiver. Requires independently verified stream metadata.

No Bluetooth discovery, streaming daemon, or recording starts on import.
"""
from __future__ import annotations
import importlib.util
import math
import time
from modules.muse.acquisition.store import Recorder
from scenescore.contracts import validate


def health():
    return {"status": "unverified", "code": "HARDWARE_UNVERIFIED",
            "reason": "No consented live session or headset/rate/unit verification performed",
            "optional_pylsl_installed": importlib.util.find_spec("pylsl") is not None,
            "implemented_modes": ["synthetic", "replay", "operator_started_lsl"],
            "recording": False}


def capture_lsl(path, metadata, *, source_id, seconds, consent, stop=None, report=print):
    validate(metadata)
    if (not consent or metadata["provenance"]["source_mode"] != "real_device"
            or not metadata["hardware_verified"] or metadata["transport"] != "lsl"
            or not source_id or not 0 < seconds <= 600):
        raise ValueError("explicit_consent_verified_lsl_metadata_and_600s_budget_required")
    try:
        import pylsl
    except ImportError as exc:
        raise RuntimeError("OPTIONAL_DEPENDENCY_UNAVAILABLE:pylsl; no capture started") from exc
    streams = pylsl.resolve_byprop("source_id", source_id, minimum=1, timeout=2)
    if len(streams) != 1:
        raise RuntimeError("exactly_one_verified_source_required")
    info = streams[0]
    if info.channel_count() != len(metadata["channels"]) or info.nominal_srate() != metadata["sample_rate_hz"]:
        raise ValueError("lsl_metadata_mismatch")
    # Full XML descriptor must agree: neither channel order nor units is guessed.
    channel = info.desc().child("channels").child("channel")
    for expected in metadata["channels"]:
        if channel.child_value("label") != expected["name"] or channel.child_value("unit") != expected["unit"]:
            raise ValueError("lsl_channel_or_unit_unverified")
        channel = channel.next_sibling()
    inlet = pylsl.StreamInlet(info, max_buflen=10, recover=False)
    recorder = None
    reason = "budget_complete"
    sequence, index, previous_time, last_received = 0, 0, None, time.monotonic()
    start = last_received
    try:
        recorder = Recorder(path, metadata, explicitly_started=True)
        report("RECORDING real_device locally; Ctrl-C stops; controls DISARMED; no upload")
        while time.monotonic()-start < seconds and not (stop and stop.is_set()):
            rows, timestamps = inlet.pull_chunk(timeout=.1, max_samples=256)
            received = time.monotonic()
            if not timestamps:
                if received-last_received > 2:
                    reason = "stream_timeout_disconnect_rearm_required"
                    break
                continue
            last_received = received
            if previous_time is not None and timestamps[0] <= previous_time:
                raise ValueError("timestamp_reset_restart_session_and_rearm")
            # LSL timestamp holes estimate loss; exact device packet counters are unavailable.
            gap = 0 if previous_time is None else max(0, round((timestamps[0]-previous_time)*metadata["sample_rate_hz"])-1)
            internal_gap = any(b-a > 1.5/metadata["sample_rate_hz"] for a, b in zip(timestamps, timestamps[1:]))
            # Split to preserve gap counts for every sample; batch arrival remains distinct.
            for row, timestamp in zip(rows, timestamps):
                if not all(math.isfinite(x) for x in row) or not math.isfinite(timestamp):
                    raise ValueError("nonfinite_device_sample")
                gap = 0 if previous_time is None else max(0, round((timestamp-previous_time)*metadata["sample_rate_hz"])-1)
                chunk = {"kind": "EEGChunk", "schema_version": "0.1", "id": metadata["session_id"] + f'-chunk-{sequence}',
                         "provenance": metadata["provenance"], "session_id": metadata["session_id"],
                         "sequence": sequence, "sample_start_index": index+gap,
                         "sample_rate_hz": metadata["sample_rate_hz"], "channels": metadata["channels"],
                         "device_times_s": [timestamp], "device_epoch": metadata["clock_epoch"],
                         "host_receipt": {"seconds": received, "clock": "host_monotonic",
                                          "epoch": metadata["clock_epoch"] + "-host"},
                         "samples": [row], "dropped_samples_before": gap,
                         "quality": {"state": "unverified", "reason": "contact_quality_not_supplied_by_LSL"}, "imu": None}
                recorder.append(chunk)
                sequence, index, previous_time = sequence+1, index+gap+1, timestamp
            report({"mode": "real_device", "samples": index, "receipt_s": received,
                    "source_s": timestamps[-1], "quality": "unverified", "gap_estimate": gap,
                    "internal_gap": internal_gap, "raw_channels": dict(zip([c["name"] for c in metadata["channels"]], rows[-1])),
                    "controls": "DISARMED"})
        if stop and stop.is_set():
            reason = "cancelled"
    except KeyboardInterrupt:
        reason = "user_stop"
    except Exception:
        reason = "fault_disconnect_rearm_required"
        raise
    finally:
        try:
            inlet.close_stream()
        finally:
            if recorder:
                recorder.close(reason)
    return {"status": reason, "chunks": sequence, "recording": False}
