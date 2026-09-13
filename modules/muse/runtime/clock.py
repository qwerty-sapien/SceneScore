"""Explicit affine mappings; no implicit relationship between clock epochs."""

import math
from copy import deepcopy

from scenescore.contracts import validate


def clock_mapping(*, identifier, provenance, source_clock, destination_clock,
                  source_epoch, destination_epoch, anchors, uncertainty_s,
                  valid_from_s, valid_until_s):
    """Fit two *supplied* synchronized anchor pairs, not wall-clock guesses.

    Transport measurements/uncertainty remain the caller's responsibility. These
    arithmetic checks establish mapping validity, not hardware synchronization.
    """
    if len(anchors) != 2 or any(len(pair) != 2 for pair in anchors):
        raise ValueError("two_clock_anchors_required")
    (s0, d0), (s1, d1) = anchors
    if not all(math.isfinite(v) for v in (s0, d0, s1, d1)) or s1 <= s0 or d1 <= d0:
        raise ValueError("invalid_clock_anchors")
    mapping = {"kind": "ClockMapping", "schema_version": "0.1", "id": identifier,
               "provenance": deepcopy(provenance), "source_clock": source_clock,
               "destination_clock": destination_clock, "source_epoch": source_epoch,
               "destination_epoch": destination_epoch, "source_anchor_s": s0,
               "destination_anchor_s": d0, "rate": (d1 - d0) / (s1 - s0),
               "uncertainty_s": uncertainty_s, "valid_from_s": valid_from_s,
               "valid_until_s": valid_until_s}
    validate(mapping)
    return mapping


def convert(mapping, stamp, *, destination_clock, destination_epoch,
            max_uncertainty_s=0.020):
    """Validity window is in source-clock seconds; inclusive endpoints."""
    try:
        validate(mapping)
        value = stamp["seconds"]
        if (mapping["kind"] != "ClockMapping" or not math.isfinite(value)
                or stamp["clock"] != mapping["source_clock"]
                or stamp["epoch"] != mapping["source_epoch"]
                or destination_clock != mapping["destination_clock"]
                or destination_epoch != mapping["destination_epoch"]
                or not mapping["valid_from_s"] <= value <= mapping["valid_until_s"]
                or not math.isfinite(max_uncertainty_s) or max_uncertainty_s < 0
                or mapping["uncertainty_s"] > max_uncertainty_s):
            raise ValueError("unmapped_or_stale_clock")
        result = mapping["destination_anchor_s"] + (value - mapping["source_anchor_s"]) * mapping["rate"]
        if not math.isfinite(result) or result < 0:
            raise ValueError("unmapped_or_stale_clock")
        return {"seconds": result, "clock": destination_clock, "epoch": destination_epoch}
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("unmapped_or_stale_clock") from exc
