"""Thin in-process dispatch adapter. Browser transport remains the audio owner."""

from copy import deepcopy
import math

from scenescore.contracts import validate
from .adapter import VERSION


def attach_receipt(envelope, decision):
    """Use actual engine stamps. Never relabel scene seconds as audio seconds.

    arrival_audio_s is the tonic arrival; boundary_s in the existing Timeline is
    the earlier scene-time pivot and cannot substitute for this stamp.
    """
    if envelope["version"] != VERSION or decision["id"] != envelope["action"]["id"]:
        raise ValueError("receipt_identity_mismatch")
    result = deepcopy(envelope)
    timing = result["timing"]
    for field, source, missing in (
        ("t4_received_s", "audio_received_s", "engine_receipt_unavailable"),
        ("t5_ack_onset_s", "ack_onset_audio_s", "engine_ack_onset_unavailable"),
        ("t6_boundary_s", "arrival_audio_s", "engine_tonic_arrival_unavailable"),
    ):
        value = decision.get(source)
        if value is None:
            timing[field] = None
            timing["unavailable_reasons"][field] = missing
        elif not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid_engine_timestamp")
        else:
            timing[field] = value
            timing["unavailable_reasons"].pop(field, None)
    return result


def dispatch(envelope, submit, *, audio_now_s, scene_now_s):
    """One callback invocation. The target performs its existing validation.

    `submit(action, audio_now_s, scene_now_s)` is synchronous and must be the
    owning music executor, never a retrying network client or alternate engine.
    """
    if envelope["version"] != VERSION:
        raise ValueError("unsupported_control_envelope")
    validate(envelope["action"])
    decision = submit(deepcopy(envelope["action"]), audio_now_s, scene_now_s)
    return {"decision": decision, "envelope": attach_receipt(envelope, decision)}
