"""Fake-clock reference behavior for contract tests, not a production audio engine."""
import math
from .contracts import validate


def map_clock(mapping, seconds, source_epoch):
    validate(mapping)
    if source_epoch != mapping["source_epoch"] or not mapping["valid_from_s"] <= seconds <= mapping["valid_until_s"]:
        raise ValueError("stale_clock")
    return mapping["destination_anchor_s"] + (seconds - mapping["source_anchor_s"]) * mapping["rate"]


def classify_closed_sequence(count, profile="double_modulate_mvp", closed=True):
    if not closed:
        return "pending"
    if profile not in ("double_modulate_mvp", "multi_count_expression_experiment"):
        raise ValueError("unknown_profile")
    if count == 2:
        return "request_modulation"
    if count == 3 and profile == "multi_count_expression_experiment":
        return "toggle_approved_expression_preset"
    return "none"


class FakeScheduler:
    def __init__(self, epoch="fixture-1", now=2.0):
        self.epoch, self.now = epoch, now
        self.seen = set()
        self.sequences = set()
        self.queue = []

    def reset(self, epoch, now):
        self.epoch, self.now = epoch, now
        self.queue.clear()
        # IDs remain remembered, even after seek/reconnect.

    def submit(self, action, mapped_request_s, mapped_expiry_s, bar_seconds=2.5, horizon=.1):
        validate(action)
        if action["status"] == "suppressed":
            return action["reason"]
        if action["request"]["epoch"] != self.epoch:
            return "stale_epoch"
        if action["id"] in self.seen or action["sequence_id"] in self.sequences:
            return "duplicate"
        if mapped_request_s > self.now or mapped_expiry_s <= self.now:
            return "future_or_expired"
        if bar_seconds <= 0 or horizon < 0:
            raise ValueError("scheduler_parameters")
        boundary = math.ceil((self.now + horizon) / bar_seconds) * bar_seconds
        if boundary >= mapped_expiry_s:
            return "expired_before_boundary"
        self.seen.add(action["id"])
        self.sequences.add(action["sequence_id"])
        self.queue.append({"action_id": action["id"], "time_s": boundary, "lanes": dict(action["after"])})
        return "queued"


def validate_chunks(chunks):
    previous = None
    for chunk in chunks:
        validate(chunk)
        if previous:
            if chunk["session_id"] != previous["session_id"] or chunk["device_epoch"] != previous["device_epoch"] or chunk["host_receipt"]["epoch"] != previous["host_receipt"]["epoch"]:
                raise ValueError("stream_epoch_changed")
            expected = previous["sample_start_index"] + len(previous["samples"]) + chunk["dropped_samples_before"]
            if chunk["sequence"] <= previous["sequence"] or chunk["sample_start_index"] != expected:
                raise ValueError("duplicate_or_unaccounted_gap")
            if previous["device_times_s"] and chunk["device_times_s"] and chunk["device_times_s"][0] <= previous["device_times_s"][-1]:
                raise ValueError("stale_device_time")
        previous = chunk
