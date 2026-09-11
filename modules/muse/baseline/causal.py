"""NEW exploratory causal candidate detector and closure grammar; not trained."""
from dataclasses import asdict, dataclass
from collections import deque
import hashlib
import math
import statistics
from modules.muse.acquisition.store import encoded
from scenescore.contracts import validate


@dataclass(frozen=True)
class Config:
    warmup_s: float = 1.0
    baseline_window_s: float = 3.0
    lowpass_hz: float = 10.0
    high_z: float = 5.0
    low_z: float = 2.0
    floor_uv: float = 7.0
    min_duration_s: float = .04
    max_duration_s: float = .4
    min_separation_s: float = .10
    max_gap_s: float = .5
    cooldown_s: float = .25

    def __post_init__(self):
        if any(not math.isfinite(x) or x <= 0 for x in asdict(self).values()):
            raise ValueError("positive_finite_config_required")
        if not (self.low_z < self.high_z and self.min_duration_s < self.max_duration_s
                and self.min_separation_s < self.max_gap_s and self.warmup_s <= self.baseline_window_s):
            raise ValueError("config_order")

    @property
    def digest(self):
        return hashlib.sha256(encoded(asdict(self))).hexdigest()


def stamp(seconds, epoch):
    return {"seconds": seconds, "clock": "device", "epoch": epoch}


def record(kind, identifier, metadata, config):
    return {"kind": kind, "schema_version": "0.1", "id": metadata["session_id"] + "-" + identifier,
            "session_id": metadata["session_id"], "provenance": {
                "source_mode": metadata["provenance"]["source_mode"], "creator": "scenescore-muse",
                "tool_version": "2A.1", "config_hash": config.digest,
                "input_hashes": [], "seed": None}}


class Grammar:
    """Closure before commitment; triples/long trains rejected, never a prefix double."""
    def __init__(self, metadata, config=Config()):
        self.metadata, self.config = metadata, config
        self.pending, self.seen = [], set()
        self.cooldown_until, self.last_time = -math.inf, -math.inf
        self.number, self.ambiguous = 0, False
        self.last_rejection = None

    def reset(self):
        self.pending.clear()
        self.seen.clear()
        self.cooldown_until, self.last_time = -math.inf, -math.inf
        self.ambiguous = False

    def feed(self, candidate):
        validate(candidate)
        if candidate["kind"] != "BlinkCandidate" or candidate["session_id"] != self.metadata["session_id"]:
            raise ValueError("candidate_session")
        if candidate["id"] in self.seen:
            return []
        onset = candidate["start"]["seconds"]
        if onset < self.last_time:
            raise ValueError("stale_candidate")
        if self.pending and candidate["start"]["epoch"] != self.pending[0]["start"]["epoch"]:
            self.reset()
        emitted = self.advance(onset)
        self.last_time = candidate["end"]["seconds"]
        self.seen.add(candidate["id"])
        # Bounded de-dup cache; monotonic time still rejects old events.
        if len(self.seen) > 4096:
            self.seen = {item["id"] for item in self.pending} | {candidate["id"]}
        if self.pending and onset - self.pending[-1]["end"]["seconds"] < self.config.min_separation_s:
            self.ambiguous = True
        self.ambiguous |= onset < self.cooldown_until or candidate["quality"]["state"] != "good"
        self.pending.append(candidate)
        # Freeze only first four candidates, retaining latest end to bound pathological trains.
        if len(self.pending) > 4:
            self.pending[-2:] = [candidate]
            self.ambiguous = True
        return emitted

    def advance(self, now):
        if not math.isfinite(now) or now < self.last_time:
            raise ValueError("nonmonotonic_grammar_clock")
        self.last_time = now
        if not self.pending or now <= self.pending[-1]["end"]["seconds"] + self.config.max_gap_s:
            return []
        last = self.pending[-1]["end"]["seconds"]
        decision = now
        if len(self.pending) > 3:
            self.last_rejection = {"reason": "overlong_train", "final_blink_s": last, "decision_s": now}
            self.pending.clear()
            self.ambiguous = False
            return []
        accepted = len(self.pending) == 2 and not self.ambiguous
        event = record("GestureEvent", f'gesture-{self.number}', self.metadata, self.config)
        event.update(candidate_ids=[x["id"] for x in self.pending], gesture_count=len(self.pending),
                     start=self.pending[0]["start"], end=self.pending[-1]["end"],
                     final_blink=self.pending[-1]["end"], decision=stamp(decision, self.pending[-1]["end"]["epoch"]),
                     closure_delay_s=decision-last, grammar_hash=self.config.digest,
                     status="accepted" if accepted else "rejected",
                     reason=None if accepted else "single_triple_or_ambiguous_train",
                     quality=next((x["quality"] for x in self.pending if x["quality"]["state"] != "good"),
                                  {"state": "good", "reason": None}))
        self.number += 1
        self.pending.clear()
        self.ambiguous = False
        if accepted:
            self.cooldown_until = decision + self.config.cooldown_s
        validate(event)
        return [event]


class CausalBaseline:
    version = "scenescore-new-causal-median/1"

    def __init__(self, metadata, config=Config()):
        validate(metadata)
        self.metadata, self.config = metadata, config
        self.indices = [i for i, c in enumerate(metadata["channels"])
                        if c["enabled"] and c["name"].lower().startswith(("af", "fp")) and c["unit"] == "uV"]
        if not self.indices:
            raise ValueError("verified_frontal_uV_channels_required")
        self.rate = metadata["sample_rate_hz"]
        if not 1 <= self.rate <= 4096 or config.lowpass_hz >= self.rate / 2:
            raise ValueError("unsupported_rate_or_filter")
        self.grammar = Grammar(metadata, config)
        self.number, self.previous = 0, None
        self.reset("startup")

    def reset(self, reason):
        self.armed, self.reason = False, reason
        self.filtered = [None] * len(self.indices)
        self.history = [deque(maxlen=min(8192, math.ceil(self.rate * self.config.baseline_window_s)))
                        for _ in self.indices]
        self.count, self.active, self.peak = 0, None, 0.0
        self.last_end, self.too_long = -math.inf, False
        self.grammar.reset()

    def arm(self):
        if self.count < math.ceil(self.rate * self.config.warmup_s) or self.reason == "bad_quality":
            raise ValueError("warmup_or_quality_not_ready")
        self.armed, self.reason = True, "armed"

    def consume(self, chunk):
        from modules.muse.acquisition.store import check_pair
        try:
            validate(chunk)
            if chunk["kind"] != "EEGChunk" or not chunk["samples"]:
                raise ValueError("nonempty_EEGChunk_required")
            for field in ("session_id", "channels", "sample_rate_hz"):
                if chunk[field] != self.metadata[field]:
                    raise ValueError("metadata_mismatch:" + field)
            check_pair(self.previous, chunk)
        except ValueError:
            self.reset("stream_discontinuity")
            raise
        if (chunk["dropped_samples_before"] or (self.previous is not None and
                (chunk["device_epoch"] != self.previous["device_epoch"]
                 or chunk["host_receipt"]["epoch"] != self.previous["host_receipt"]["epoch"]))):
            self.reset("gap_or_reconnect_rearm_required")
        self.previous = chunk
        if chunk["quality"]["state"] != "good":
            self.reset("bad_quality")
            return [], []
        if self.reason == "bad_quality":
            self.reason = "quality_recovered_rearm_required"
        candidates, gestures = [], []
        alpha = 1 - math.exp(-2 * math.pi * self.config.lowpass_hz / self.rate)
        for t, row in zip(chunk["device_times_s"], chunk["samples"]):
            scores = []
            for j, i in enumerate(self.indices):
                x = row[i]
                self.filtered[j] = x if self.filtered[j] is None else self.filtered[j] + alpha * (x-self.filtered[j])
                history = self.history[j]
                center = statistics.median(history) if history else self.filtered[j]
                mad = statistics.median(abs(v-center) for v in history) if history else 0
                scores.append(abs(self.filtered[j]-center) / max(1.4826*mad, self.config.floor_uv))
                if self.active is None:
                    history.append(self.filtered[j])
            self.count += 1
            score = min(scores)  # bilateral agreement, never subtract frontal channels
            if not self.armed:
                continue
            if self.active is None and score >= self.config.high_z and t-self.last_end >= self.config.min_separation_s:
                self.active, self.peak, self.too_long = t, score, False
            if self.active is not None:
                self.peak = max(self.peak, score)
                self.too_long |= t-self.active > self.config.max_duration_s
                if score <= self.config.low_z:
                    duration = t-self.active
                    if self.config.min_duration_s <= duration <= self.config.max_duration_s and not self.too_long:
                        event = record("BlinkCandidate", f'candidate-{self.number}', self.metadata, self.config)
                        event.update(start=stamp(self.active, chunk["device_epoch"]), end=stamp(t, chunk["device_epoch"]),
                                     model_version=self.version, score=self.peak, score_type="uncalibrated",
                                     quality={"state": "good", "reason": None})
                        validate(event)
                        candidates.append(event)
                        gestures.extend(self.grammar.feed(event))
                        self.number += 1
                    elif self.grammar.pending:
                        self.grammar.ambiguous = True
                    self.active, self.last_end = None, t
            # An in-progress waveform can still close as a third blink: do not commit its prefix.
            if self.active is None:
                gestures.extend(self.grammar.advance(t))
        return candidates, gestures
