"""Deterministic raw-session replay through the production causal candidate/grammar path."""
from __future__ import annotations

import math

from modules.muse.acquisition.store import manifest, replay
from modules.muse.baseline.causal import CausalBaseline, Config


def replay_session(path, *, config=None, arm_after_s=None):
    config = config or Config()
    if arm_after_s is not None and (not math.isfinite(arm_after_s) or arm_after_s < config.warmup_s):
        raise ValueError("replay_arm_time_must_allow_warmup")
    metadata = manifest(path)["metadata"]
    detector = CausalBaseline(metadata, config)
    events, faults, start, armed_once, samples = [], [], None, False, 0
    for chunk in replay(path):
        samples += len(chunk["samples"])
        if samples > 2_000_000:
            raise ValueError("replay_sample_budget_exceeded")
        start = chunk["device_times_s"][0] if start is None else start
        previously_armed = detector.armed
        candidates, gestures = detector.consume(chunk)
        events.extend(candidates + gestures)
        if previously_armed and not detector.armed:
            faults.append({"sequence": chunk["sequence"], "reason": detector.reason, "rearm_required": True})
        if arm_after_s is not None and not armed_once and chunk["device_times_s"][-1] - start >= arm_after_s:
            # One explicit initial arm attempt. A fault never silently re-arms the stream.
            armed_once = True
            try:
                detector.arm()
            except ValueError as exc:
                faults.append({"sequence": chunk["sequence"], "reason": str(exc), "rearm_required": True})
    # No future sample/clock is invented at EOF to close a pending sequence.
    return {"format": "scenescore.causal-replay/1", "mode": "replay",
            "recording_source_mode": metadata["provenance"]["source_mode"],
            "config_sha256": config.digest, "events": events, "faults": faults,
            "samples": samples, "armed_at_end": detector.armed,
            "pending_candidates_at_eof": len(detector.grammar.pending),
            "real_performance": "NOT_RUN"}
