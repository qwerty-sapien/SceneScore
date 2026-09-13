"""Explicit, bounded discovery of advertised LSL metadata; never pulls samples."""
from __future__ import annotations

import math


def diagnose_transport(*, source_id=None, timeout_s=2.0):
    if not math.isfinite(timeout_s) or not 0 < timeout_s <= 5:
        raise ValueError("diagnostic_timeout_must_be_in_0_to_5_seconds")
    result = {
        "format": "scenescore.transport-diagnostic/1",
        "transport": "lsl",
        "recording": False,
        "samples_read": 0,
        "hardware_verified": False,
        "device_model": None,
        "firmware": None,
        "verified_sample_rate_hz": None,
        "streams": [],
        "reason": None,
    }
    try:
        import pylsl
    except (ImportError, RuntimeError, OSError) as exc:
        return {**result, "status": "BLOCKED", "code": "OPTIONAL_DEPENDENCY_UNAVAILABLE",
                "reason": "pylsl or its native liblsl could not load", "detail": str(exc)}
    try:
        streams = (pylsl.resolve_byprop("source_id", source_id, minimum=1, timeout=timeout_s)
                   if source_id else pylsl.resolve_streams(wait_time=timeout_s))
        if len(streams) > 64:
            raise ValueError("diagnostic_stream_budget_exceeded")
        for info in streams:
            channel_count = info.channel_count()
            if not 1 <= channel_count <= 256:
                raise ValueError("diagnostic_channel_budget_exceeded")
            channel = info.desc().child("channels").child("channel")
            channels = []
            for index in range(channel_count):
                channels.append({"index": index, "name": channel.child_value("label") or None,
                                 "unit": channel.child_value("unit") or None})
                channel = channel.next_sibling()
            rate = info.nominal_srate()
            result["streams"].append({"source_id": info.source_id(), "name": info.name(),
                                      "type": info.type(), "channel_count": channel_count,
                                      "advertised_sample_rate_hz": rate if math.isfinite(rate) and rate > 0 else None,
                                      "channels": channels,
                                      "metadata_complete": all(c["name"] and c["unit"] for c in channels),
                                      "verified": False})
    except (RuntimeError, OSError) as exc:
        return {**result, "status": "BLOCKED", "code": "TRANSPORT_DISCOVERY_FAILED", "reason": str(exc)}
    if not result["streams"]:
        return {**result, "status": "BLOCKED", "code": "NO_ADVERTISED_LSL_STREAM",
                "reason": "No matching LSL source advertised during the bounded metadata check"}
    return {**result, "status": "METADATA_OBSERVED_UNVERIFIED", "code": "HARDWARE_UNVERIFIED",
            "reason": "Advertised metadata is not a measured rate, contact-quality check, or headset verification; missing fields stay null"}
