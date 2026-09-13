"""Canonical closed-gesture -> canonical control, with versioned diagnostics.

No I/O, inference, music policy or scheduling occurs in this module. MusicContext
must come from the music owner's policy evaluated at the mapped decision time.
"""

from copy import deepcopy
from dataclasses import dataclass
import math

from modules.muse.baseline.causal import Config, Grammar
from scenescore.contracts import validate
from .clock import convert


VERSION = "muse-control-envelope-1"
SOURCE_MODES = {"real_device", "replay", "synthetic", "keyboard"}
FAULTS = {"dropout", "quality_loss", "reconnect", "refit", "model_reload", "stream_discontinuity"}
REASONS = FAULTS | {"startup", "disarmed", "warmup_or_rearm_required", "invalid_candidate_duration",
    "candidate_session_or_epoch", "gesture_session_or_epoch", "nonmonotonic_stream", "duplicate",
    "dedup_capacity_rearm_insufficient", "experimental_or_invalid_action", "quality_gate",
    "closure_not_complete", "grammar_mismatch", "unmapped_or_stale_clock", "music_context_required",
    "stale_plan", "stationary_world_z", "single_triple_or_ambiguous_train", "overlong_train",
    "upstream_suppression"}


@dataclass(frozen=True)
class MusicContext:
    approved_plan_hash: str | None
    scene_policy_id: str | None
    signed_semitones: int
    lanes: dict
    expires_after_s: float = 6.0
    suppression_reason: str | None = None

    def __post_init__(self):
        if self.signed_semitones not in (-2, 0, 2):
            raise ValueError("invalid_music_direction")
        if not math.isfinite(self.expires_after_s) or not 0 < self.expires_after_s <= 30:
            raise ValueError("expiry_bound")


def rejected(reason):
    return {"envelope": None, "reason": reason}


class RuntimeAdapter:
    """One adapter per session/epoch. Faults clear grammar but never dedup history.

    `feed`/`advance` use the repository Grammar for candidate fixture/replay paths.
    `accept` consumes closed GestureEvents from CausalBaseline's own Grammar.
    Neither method authorizes live acquisition or supplies human truth labels.
    """

    def __init__(self, metadata, device_epoch, config=Config(), started_device_s=0.0,
                 model_version="scenescore-new-causal-median/1"):
        validate(metadata)
        if metadata["kind"] != "AcquisitionMetadata" or metadata["provenance"]["source_mode"] not in SOURCE_MODES:
            raise ValueError("unsupported_acquisition_provenance")
        self.metadata = deepcopy(metadata)
        self.device_epoch, self.config, self.model_version = device_epoch, config, model_version
        self.grammar = Grammar(metadata, config)
        self.context = self.mapping = self.host_epoch = None
        self.seen_ids, self.seen_sequences, self.seen_candidates = set(), set(), set()
        self.seen_gesture_candidates = set()
        self.armed, self.reason = False, "startup"
        self.started_device_s = self.last_device_s = self._time(started_device_s)
        self.last_rejection = None

    @staticmethod
    def _time(value):
        if not math.isfinite(value) or value < 0:
            raise ValueError("invalid_runtime_time")
        return value

    def configure(self, context, mapping, host_epoch):
        if not isinstance(context, MusicContext) or not host_epoch:
            raise ValueError("music_context_required")
        validate(mapping)
        if (mapping["kind"] != "ClockMapping" or mapping["source_clock"] != "device"
                or mapping["source_epoch"] != self.device_epoch or mapping["destination_clock"] != "audio"):
            raise ValueError("unmapped_or_stale_clock")
        self.context, self.mapping, self.host_epoch = deepcopy(context), deepcopy(mapping), host_epoch

    def status(self, device_now_s):
        now = self._time(device_now_s)
        return {"version": "muse-runtime-status-1", "source_mode": self.metadata["provenance"]["source_mode"],
                "armed": self.armed, "reason": self.reason, "device_epoch": self.device_epoch,
                "warmup_ready": now >= self.started_device_s + self.config.warmup_s,
                "pending_candidate_count": len(self.grammar.pending), "last_rejection": self.last_rejection}

    def arm(self, device_now_s):
        now = self._time(device_now_s)
        if now < self.last_device_s or now < self.started_device_s + self.config.warmup_s:
            raise ValueError("warmup_or_rearm_required")
        self.armed, self.reason = True, "armed"

    def fault(self, reason, device_now_s):
        if reason not in FAULTS:
            raise ValueError("unknown_runtime_fault")
        self._reset(reason, device_now_s)

    def disarm(self, device_now_s):
        self._reset("disarmed", device_now_s)

    def _reset(self, reason, device_now_s):
        now = self._time(device_now_s)
        self.grammar.reset()
        self.armed, self.reason = False, reason
        self.started_device_s, self.last_device_s = now, now
        self.last_rejection = reason

    def _reject(self, reason):
        self.last_rejection = reason
        return rejected(reason)

    def feed(self, candidate, host_now_s):
        validate(candidate)
        if (candidate["kind"] != "BlinkCandidate" or candidate["session_id"] != self.metadata["session_id"]
                or candidate["start"]["epoch"] != self.device_epoch or candidate["start"]["clock"] != "device"):
            return [self._reject("candidate_session_or_epoch")]
        if candidate["id"] in self.seen_candidates:
            return [self._reject("duplicate")]
        if len(self.seen_candidates) >= 4096:
            return [self._reject("dedup_capacity_rearm_insufficient")]
        self.seen_candidates.add(candidate["id"])
        start, end = candidate["start"]["seconds"], candidate["end"]["seconds"]
        if start < self.last_device_s:
            self._reset("stream_discontinuity", self.last_device_s)
            return [self._reject("nonmonotonic_stream")]
        if candidate["quality"]["state"] != "good":
            self.fault("quality_loss", end)
            return [self._reject("quality_gate")]
        if not self.armed or start < self.started_device_s + self.config.warmup_s:
            self.last_device_s = end
            return [self._reject("warmup_or_rearm_required")]
        if not self.config.min_duration_s <= end - start <= self.config.max_duration_s:
            # An invalid waveform within a pending train must not make its prefix
            # look like a clean double. Continue requiring sequence closure.
            if self.grammar.pending:
                self.grammar.ambiguous = True
            self.last_device_s = end
            return [self._reject("invalid_candidate_duration")]
        try:
            gestures = self.grammar.feed(candidate)
        except ValueError:
            self.fault("stream_discontinuity", end)
            return [self._reject("nonmonotonic_stream")]
        self.last_device_s = end
        return [self.accept(gesture, host_now_s) for gesture in gestures]

    def advance(self, device_now_s, host_now_s):
        now = self._time(device_now_s)
        if now < self.last_device_s:
            self.fault("stream_discontinuity", self.last_device_s)
            return [self._reject("nonmonotonic_stream")]
        self.last_device_s = now
        if not self.armed:
            return []
        self.grammar.last_rejection = None
        events = self.grammar.advance(now)
        results = [self.accept(gesture, host_now_s) for gesture in events]
        if self.grammar.last_rejection:
            results.append(self._reject(self.grammar.last_rejection["reason"]))
        return results

    def accept(self, gesture, host_now_s):
        validate(gesture)
        self._time(host_now_s)
        if (gesture["kind"] != "GestureEvent" or gesture["session_id"] != self.metadata["session_id"]
                or gesture["decision"]["epoch"] != self.device_epoch or gesture["decision"]["clock"] != "device"
                or gesture["provenance"]["source_mode"] != self.metadata["provenance"]["source_mode"]):
            return self._reject("gesture_session_or_epoch")
        sequence = gesture["id"]
        identifier = "control:" + sequence
        if (sequence in self.seen_sequences or identifier in self.seen_ids
                or any(identifier in self.seen_gesture_candidates for identifier in gesture["candidate_ids"])):
            return self._reject("duplicate")
        if len(self.seen_sequences) >= 4096:
            return self._reject("dedup_capacity_rearm_insufficient")
        # A rejected/suppressed event is consumed too: never retry it after rearm.
        self.seen_sequences.add(sequence)
        self.seen_ids.add(identifier)
        self.seen_gesture_candidates.update(gesture["candidate_ids"])
        if not self.armed or gesture["start"]["seconds"] < self.started_device_s + self.config.warmup_s:
            return self._reject("warmup_or_rearm_required")
        if gesture["status"] != "accepted":
            return self._reject("single_triple_or_ambiguous_train")
        if gesture["gesture_count"] != 2:
            return self._reject("experimental_or_invalid_action")
        if gesture["quality"]["state"] != "good":
            self.fault("quality_loss", gesture["decision"]["seconds"])
            return self._reject("quality_gate")
        if gesture["grammar_hash"] != self.config.digest:
            return self._reject("grammar_mismatch")
        if (gesture["final_blink"] != gesture["end"]
                or gesture["closure_delay_s"] <= self.config.max_gap_s):
            return self._reject("closure_not_complete")
        if self.context is None or self.mapping is None or self.host_epoch is None:
            return self._reject("music_context_required")
        try:
            request = convert(self.mapping, gesture["decision"], destination_clock="audio",
                              destination_epoch=self.mapping["destination_epoch"])
        except ValueError:
            return self._reject("unmapped_or_stale_clock")
        context = self.context
        reason = context.suppression_reason
        if context.approved_plan_hash is None or context.scene_policy_id is None:
            reason = reason or "stale_plan"
        if context.signed_semitones == 0:
            reason = reason or "stationary_world_z"
        action = {"kind": "ControlAction", "schema_version": "0.1", "id": identifier,
            "provenance": deepcopy(gesture["provenance"]), "gesture_id": sequence, "sequence_id": sequence,
            "gesture_count": 2, "profile": "double_modulate_mvp",
            "action": "request_modulation" if context.signed_semitones else "none",
            "request": request, "expires": {**request, "seconds": request["seconds"] + context.expires_after_s},
            "boundary": "next_approved_bar_or_phrase", "signed_semitones": context.signed_semitones,
            "scene_policy_id": context.scene_policy_id, "approved_plan_hash": context.approved_plan_hash,
            "status": "suppressed" if reason else "queued", "reason": reason,
            "quality": deepcopy(gesture["quality"]), "before": deepcopy(context.lanes), "after": deepcopy(context.lanes)}
        validate(action)
        envelope = {"version": VERSION, "action": action,
            "detector": {"version": "muse-runtime-1", "model_version": self.model_version,
                         "grammar_hash": self.config.digest},
            "timing": {"t0_final_blink_s": gesture["final_blink"]["seconds"],
                "t1_decision_s": gesture["decision"]["seconds"], "t2_dispatch_s": host_now_s,
                "t3_request_s": request["seconds"], "t4_received_s": None,
                "t5_ack_onset_s": None, "t6_boundary_s": None,
                "device_epoch": self.device_epoch, "host_epoch": self.host_epoch,
                "audio_epoch": request["epoch"], "clock_mapping_id": self.mapping["id"],
                "unavailable_reasons": {"t4_received_s": "awaiting_music_receipt",
                    "t5_ack_onset_s": "awaiting_music_scheduler", "t6_boundary_s": "awaiting_music_scheduler",
                    "dispatch_after_decision_ms": "device_to_host_mapping_not_supplied"}}}
        return {"envelope": envelope, "reason": reason}
