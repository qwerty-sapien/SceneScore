"""Bounded data-only arrangement compiler against frozen contract 0.1."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

from scenescore.contracts import approved_payload, validate, validate_bundle
from . import VERSION


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


@dataclass(frozen=True)
class Policy:
    """Versioned editable sidecar; exact settings are bound into plan.config_hash."""
    smoothing_s: float = 0.15
    hysteresis_m: float = 0.02
    anticipation_s: float = 0.5
    release_s: float = 0.5
    max_voices: int = 12
    max_events_per_second: int = 80
    max_objects: int = 3
    gain_db: float = -12
    lookback_s: float = 0.3
    deadband_m_s: float = 0.02

    def __post_init__(self):
        limits = {"smoothing_s": (.01, 2), "hysteresis_m": (0, 1),
                  "anticipation_s": (0, 2), "release_s": (.01, 2),
                  "max_voices": (6, 24), "max_events_per_second": (8, 200),
                  "max_objects": (1, 3), "gain_db": (-36, -3),
                  "lookback_s": (.05, 1), "deadband_m_s": (0, 2)}
        for name, (low, high) in limits.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"policy_range:{name}")
            if name.startswith("max_") and not isinstance(value, int):
                raise ValueError(f"policy_integer:{name}")


@dataclass
class Context:
    scene: dict
    states: list[dict]
    interactions: list[dict]
    composition: dict
    groove: dict

    def __post_init__(self):
        if len(self.states) > 30000 or len(self.interactions) > 512 or len(self.scene.get("objects", [])) > 64:
            raise ValueError("scene_record_budget")
        validate_bundle([self.scene, *self.states, *self.interactions, self.composition, self.groove])
        if self.scene["duration_s"] > 120 or len(self.composition["notes"]) > 4096 or tick_seconds(self.composition, self.composition["length_ticks"]) > 120:
            raise ValueError("preview_duration_or_note_budget")
        if not self.scene["objects"]:
            raise ValueError("empty_scene")
        for record in [*self.states, *self.interactions]:
            at = record.get("scene_time_s", record.get("onset_s", 0))
            end = at + record.get("duration_s", 0)
            if at < 0 or end > self.scene["duration_s"] + 1e-6:
                raise ValueError("scene_time_outside_duration")
        if len(self.composition["key_map"]) != 1 or self.composition["key_map"][0]["mode"] not in ("major", "minor", "blues_centre"):
            raise ValueError("unsupported_key_policy")
        if self.composition["ppq"] != self.groove["ppq"] or self.composition["meter"] != self.groove["meter"]:
            raise ValueError("groove_clock_mismatch")
        for object_id in self.objects:
            times = [s["scene_time_s"] for s in self.states if s["object_id"] == object_id]
            if len(set(times)) != len(times):
                raise ValueError("duplicate_object_sample_time")

    @property
    def objects(self):
        return sorted(o["object_id"] for o in self.scene["objects"])

    @property
    def scene_hash(self):
        return digest({"scene": self.scene, "states": sorted(self.states, key=lambda s: s["id"]),
                       "interactions": sorted(self.interactions, key=lambda s: s["id"])})

    @property
    def composition_hash(self):
        return digest({"composition": self.composition, "groove": self.groove})

    @classmethod
    def from_summary(cls, summary, composition, groove):
        return cls(summary["scene"], [s for o in summary["objects"] for s in o["keyframes"]],
                   summary["events"], composition, groove)


def config_hash(policy: Policy, brief: str):
    return digest({"version": VERSION, "policy": asdict(policy), "brief": brief, "schema": "0.1"})


def provenance(ctx, policy, brief, mode="manual_plan", seed=42):
    return {"source_mode": mode, "creator": VERSION, "tool_version": VERSION,
            "config_hash": config_hash(policy, brief),
            "input_hashes": [ctx.scene_hash, ctx.composition_hash], "seed": seed}


def base_record(kind, ident, prov):
    return {"kind": kind, "schema_version": "0.1", "id": ident, "provenance": deepcopy(prov)}


INSTRUMENTS = {"piano": "keyboard_damped_v1", "bass": "bass_pluck_v1",
               "brushes": "brush_noise_v1", "foley": "arranger_contact_noise_v1"}
PALETTE = list(INSTRUMENTS.values())
# Range policy for distinct editable lanes, interpreted below (not opaque model prose).
LANES = {("approach", "ornament"): (0, 1), ("separation", "dynamics"): (-12, 0),
         ("surface_gap", "phrasing"): (0, 1), ("collision", "timbre"): (0, 1),
         ("vertical_motion", "register"): (-12, 12)}


def baseline(ctx: Context, policy=Policy(), brief="Original blues/ragtime swing; restrained bossa accompaniment", seed=42):
    prov = provenance(ctx, policy, brief, seed=seed)
    plan = base_record("ArrangementPlan", "plan-" + digest([ctx.scene_hash, ctx.composition_hash, prov])[:20], prov)
    plan.update(scene_hash=ctx.scene_hash, composition_hash=ctx.composition_hash,
                palette_ids=PALETTE[:], groove_id=ctx.groove["id"], groove_version=ctx.groove["catalog_version"],
                motif_owners=[{"object_id": o, "motif_id": "motif-" + next(x["sonic_identity_id"] for x in ctx.scene["objects"] if x["object_id"] == o)} for o in ctx.objects],
                mappings=[{"feature": f, "lane": lane, "input_min": -2 if f == "vertical_motion" else 0,
                           "input_max": 2 if f == "vertical_motion" else 1,
                           "output_min": lo, "output_max": hi} for (f, lane), (lo, hi) in LANES.items()],
                transitions=[{"from_pc": pc, "to_pc": (pc + delta) % 12, "signed_semitones": delta,
                              "mode": ctx.composition["key_map"][0]["mode"]} for pc in range(12) for delta in (-2, 2)],
                register_min=28, register_max=96,
                motion_policy={"id": "world-z-causal-1", "focus_object_id": ctx.objects[0], "axis": "Z",
                               "lookback_s": policy.lookback_s, "deadband_m_s": policy.deadband_m_s, "stationary_action": "none"},
                uncertainties=["Artistic geometry mapping, not acoustic or emotional inference.",
                               "AUDITION_PENDING; direct dominant-to-tonic arrivals require listening.",
                               "Objects beyond configured voice budget retain identity but are silent."], review_status="draft")
    return validate_plan(plan, ctx, policy, brief)


def validate_plan(plan, ctx, policy, brief):
    validate(plan)
    if plan["scene_hash"] != ctx.scene_hash or plan["composition_hash"] != ctx.composition_hash:
        raise ValueError("stale_asset_hash")
    if plan["provenance"]["config_hash"] != config_hash(policy, brief):
        raise ValueError("stale_policy_or_brief")
    if set(plan["palette_ids"]) != set(PALETTE):
        raise ValueError("unknown_or_missing_palette")
    if (plan["groove_id"], plan["groove_version"]) != (ctx.groove["id"], ctx.groove["catalog_version"]):
        raise ValueError("unknown_groove")
    if sorted(m["object_id"] for m in plan["motif_owners"]) != ctx.objects:
        raise ValueError("unknown_or_missing_object")
    if len({m["motif_id"] for m in plan["motif_owners"]}) != len(ctx.objects):
        raise ValueError("motif_identity_collision")
    if plan["register_min"] < 28 or plan["register_max"] > 96 or plan["register_max"] - plan["register_min"] < 24:
        raise ValueError("unsafe_register")
    keys = [(m["feature"], m["lane"]) for m in plan["mappings"]]
    if len(keys) != len(set(keys)) or set(keys) != set(LANES):
        raise ValueError("conflicting_or_unsupported_lanes")
    for mapping in plan["mappings"]:
        lo, hi = LANES[(mapping["feature"], mapping["lane"])]
        if not lo <= mapping["output_min"] <= mapping["output_max"] <= hi:
            raise ValueError("lane_output_bounds")
    motion = plan["motion_policy"]
    if motion["focus_object_id"] not in ctx.objects or motion["lookback_s"] != policy.lookback_s or motion["deadband_m_s"] != policy.deadband_m_s:
        raise ValueError("motion_policy_mismatch")
    mode = ctx.composition["key_map"][0]["mode"]
    if any(t["mode"] != mode for t in plan["transitions"]):
        raise ValueError("unsupported_mode_transition")
    if len({(t["from_pc"], t["signed_semitones"]) for t in plan["transitions"]}) != len(plan["transitions"]):
        raise ValueError("duplicate_transition")
    return plan


def curve(plan, feature, value):
    m = next(m for m in plan["mappings"] if m["feature"] == feature)
    unit = min(1, max(0, (value - m["input_min"]) / (m["input_max"] - m["input_min"])))
    return m["output_min"] + unit * (m["output_max"] - m["output_min"])


def tick_seconds(composition, tick):
    result = 0.0
    for i, item in enumerate(composition["tempo_map"]):
        end = composition["tempo_map"][i+1]["tick"] if i+1 < len(composition["tempo_map"]) else tick
        amount = min(tick, end) - item["tick"]
        if amount > 0:
            result += amount / composition["ppq"] * 60 / item["bpm"]
    return result


def swung_tick(c, tick, eligible):
    q = c["ppq"]
    if not eligible:
        return float(tick)
    whole, phase = divmod(tick, q)
    ratio = c["swing_ratio"]
    return whole*q + (phase*2*ratio if phase <= q/2 else q*ratio + (phase-q/2)*2*(1-ratio))


def bounded_pitch(pitch, low, high):
    while pitch < low:
        pitch += 12
    while pitch > high:
        pitch -= 12
    if not low <= pitch <= high:
        raise ValueError("unvoicable_register")
    return pitch


def motion_direction(ctx, plan, at):
    """Causal piecewise-constant average; unknown/stale coverage holds, never future samples."""
    p = plan["motion_policy"]
    start = max(0, at - p["lookback_s"])
    rows = sorted((s for s in ctx.states if s["object_id"] == p["focus_object_id"] and s["scene_time_s"] <= at), key=lambda s: s["scene_time_s"])
    if not rows or at <= start or rows[0]["scene_time_s"] > start or at - rows[-1]["scene_time_s"] > p["lookback_s"]:
        return 0
    integral = 0.0
    for i, row in enumerate(rows):
        end = rows[i+1]["scene_time_s"] if i+1 < len(rows) else at
        duration = max(0, min(end, at) - max(start, row["scene_time_s"]))
        if duration and row["velocity_m_s"] is None:
            return 0
        integral += duration * (row["velocity_m_s"][2] if row["velocity_m_s"] else 0)
    speed = integral / (at - start)
    return 0 if abs(speed) <= p["deadband_m_s"] else (2 if speed > 0 else -2)


def smoothed_z(ctx, object_id, at, policy):
    rows = sorted((s for s in ctx.states if s["object_id"] == object_id and s["scene_time_s"] <= at), key=lambda s: s["scene_time_s"])
    z, previous = 0.0, 0.0
    for row in rows:
        dt = row["scene_time_s"] - previous
        target = row["velocity_m_s"][2] if row["velocity_m_s"] else 0
        z += (1 - math.exp(-dt / policy.smoothing_s)) * (target-z)
        previous = row["scene_time_s"]
    return z if rows and at-previous <= policy.lookback_s else 0


def note_event(plan, ident, object_id, lane, instrument, tick, duration, pitch, velocity, articulation, c, policy, swingable=False):
    at = tick_seconds(c, swung_tick(c, tick, swingable))
    end = tick_seconds(c, swung_tick(c, tick+duration, swingable))
    event = base_record("ScoreEvent", ident, plan["provenance"])
    event.update(plan_id=plan["id"], object_id=object_id, lane_id=lane, event_type="note", instrument_id=INSTRUMENTS[instrument],
                 start_tick=tick, duration_ticks=duration, resolved_time_s=at, duration_s=max(.001, end-at), scene_time_s=None,
                 midi_pitch=bounded_pitch(pitch, plan["register_min"], plan["register_max"]), velocity=velocity,
                 dynamics_db=policy.gain_db, articulation=articulation, phrasing="original-call-response", ornament=None,
                 timbre_id=INSTRUMENTS[instrument], swing_applied=swingable, swing_application_count=int(swingable))
    return event


class Hysteresis:
    """Schmitt gate on the bounded smoothed feature, independent of note velocity."""
    def __init__(self):
        self.active = False

    def update(self, value):
        if value >= .6:
            self.active = True
        elif value <= .4:
            self.active = False
        return self.active


def compile_preview(ctx, plan, policy=Policy(), brief="Original blues/ragtime swing; restrained bossa accompaniment"):
    """Candidate event output for audition, NEVER implicitly approved for activation."""
    validate_plan(plan, ctx, policy, brief)
    c = ctx.composition
    events = []
    for object_id in ctx.objects[:policy.max_objects]:
        owner = next(m["motif_id"] for m in plan["motif_owners"] if m["object_id"] == object_id)
        states = sorted((s for s in ctx.states if s["object_id"] == object_id), key=lambda s: (s["scene_time_s"], s["id"]))
        area = states[0]["surface_area_m2"] if states else 1
        # Area is an explicitly artistic octave selection, not acoustic estimation.
        octave = -12 if area > 4 else (12 if area < .25 else 0)
        approach_gate = Hysteresis()
        for index, n in enumerate(sorted(c["notes"], key=lambda n: n["start_tick"])):
            e = note_event(plan, f"{object_id}:motif:{index}", object_id, owner, "piano", n["start_tick"], n["duration_ticks"],
                           n["midi_pitch"]+octave, n["velocity"], n["articulation"], c, policy, n["swingable"])
            at = e["resolved_time_s"]
            register = round(curve(plan, "vertical_motion", smoothed_z(ctx, object_id, at, policy)))
            e["midi_pitch"] = bounded_pitch(e["midi_pitch"]+register, plan["register_min"], plan["register_max"])
            approach_strength = 0.0
            for interaction in sorted(ctx.interactions, key=lambda x: (x["onset_s"], x["id"])):
                if object_id not in interaction["pair"]:
                    continue
                onset, kind = interaction["onset_s"], interaction["event_type"]
                if not onset-policy.anticipation_s <= at <= onset+interaction["duration_s"]+policy.release_s:
                    continue
                strength = 1-math.exp(-max(0, at-(onset-policy.anticipation_s))/policy.smoothing_s)
                if kind == "approach" and interaction["surface_gap_m"] > policy.hysteresis_m:
                    approach_strength = max(approach_strength, curve(plan, "approach", strength))
                elif kind == "near_miss":
                    if curve(plan, "surface_gap", 1-min(1, interaction["surface_gap_m"])) >= .5:
                        e["phrasing"] = "cadence-withheld" if at <= onset else "delayed-resolution"
                        tonic = c["key_map"][0]["tonic_pc"]
                        e["midi_pitch"] = bounded_pitch((e["midi_pitch"]//12)*12+tonic+(2 if at <= onset else 0), plan["register_min"], plan["register_max"])
                elif kind == "separation" and at >= onset:
                    fade = min(1, (at-onset)/policy.release_s)
                    e["dynamics_db"] += curve(plan, "separation", 1-fade)
            if approach_gate.update(approach_strength):
                e["ornament"] = "chromatic-anticipation"
                e["phrasing"] = "bounded-approach"
                e["midi_pitch"] = bounded_pitch(e["midi_pitch"]+1, plan["register_min"], plan["register_max"])
            # Each lane remains separately editable; bounded total dynamics.
            e["dynamics_db"] = max(-48, min(-3, e["dynamics_db"]))
            events.append(e)
    for index, chord in enumerate(c["harmony"]):
        root = 36+chord["root_pc"]
        events.append(note_event(plan, f"bass:{index}", None, "bass", "bass", chord["start_tick"], chord["duration_ticks"], root, 64, "detached", c, policy))
        for voice, interval in enumerate(chord["intervals_semitones"][:3]):
            events.append(note_event(plan, f"harmony:{index}:{voice}", None, f"harmony-{voice}", "piano", chord["start_tick"], chord["duration_ticks"], root+12+interval, 52, "legato", c, policy))
    for loop in range(0, c["length_ticks"], ctx.groove["length_ticks"]):
        for i, n in enumerate(ctx.groove["events"]):
            tick = loop+n["start_tick"]
            if tick+n["duration_ticks"] > c["length_ticks"]:
                continue
            e = note_event(plan, f"brush:{loop}:{i}", None, "brushes", "brushes", tick, n["duration_ticks"], 60, n["velocity"], n["technique"], c, policy, n["swingable"])
            e.update(event_type="brush", midi_pitch=None)
            events.append(e)
    for interaction in ctx.interactions:
        if interaction["event_type"] not in ("collision", "contact_onset", "contact_sustain", "contact_release"):
            continue
        e = base_record("ScoreEvent", "foley:"+interaction["id"], plan["provenance"])
        e.update(plan_id=plan["id"], object_id=interaction["pair"][0], lane_id="contact:"+interaction["pair_id"], event_type="foley", instrument_id=INSTRUMENTS["foley"],
                 start_tick=None, duration_ticks=None, resolved_time_s=interaction["onset_s"], duration_s=max(.01, interaction["duration_s"]), scene_time_s=interaction["onset_s"],
                 midi_pitch=None, velocity=90 if interaction["event_type"] in ("collision", "contact_onset") else 40,
                 dynamics_db=policy.gain_db, articulation=interaction["event_type"], phrasing="exact-scene-time", ornament=None,
                 timbre_id="contact-bright" if curve(plan, "collision", min(1, abs(interaction["relative_normal_speed_m_s"]))) >= .5 else "contact-soft",
                 swing_applied=False, swing_application_count=0)
        events.append(e)
    events.sort(key=lambda e: (e["resolved_time_s"], e["id"]))
    validate_event_budget(events, plan, policy)
    return events


def validate_event_budget(events, plan, policy):
    active = []
    recent = []
    for event in sorted(events, key=lambda e: (e["resolved_time_s"], e["id"])):
        validate(event)
        if event["instrument_id"] not in plan["palette_ids"] or event["plan_id"] != plan["id"]:
            raise ValueError("unknown_event_reference")
        pitch = event["midi_pitch"]
        if pitch is not None and not plan["register_min"] <= pitch <= plan["register_max"]:
            raise ValueError("pitch_outside_register")
        at = event["resolved_time_s"]
        active = [end for end in active if end > at+1e-9]
        active.append(at+event["duration_s"])
        recent = [start for start in recent if start > at-1]
        recent.append(at)
        if len(active) > policy.max_voices or len(recent) > policy.max_events_per_second:
            raise ValueError("event_budget_exceeded:edit_policy_or_score_before_approval")


def exact_diff(before, after):
    """Review exact data changes, never claim a diff is an audition."""
    return [{"field": key, "before": before.get(key), "after": after.get(key)}
            for key in sorted(set(before)|set(after)) if before.get(key) != after.get(key)]


def import_plan(payload: bytes, ctx, policy, brief):
    plan = json.loads(payload)
    validate_plan(plan, ctx, policy, brief)
    return plan  # Exact incoming bytes are separately retained for approval.


class TransitionPreview:
    """Audition-only local candidate family; never an approved performance session."""
    def __init__(self, plan, ctx, policy=Policy(), brief="Original blues/ragtime swing; restrained bossa accompaniment"):
        self._plan = deepcopy(plan)
        self._approved = False
        validate_plan(self._plan, ctx, policy, brief)
        self._ctx, self._policy = deepcopy(ctx), policy
        self._events = compile_preview(ctx, self._plan, policy, brief)
        self._plan = deepcopy(self._plan)
        self._plan_hash = digest(plan)
        self.tonic = ctx.composition["key_map"][0]["tonic_pc"]
        self.requests = set()
        self.boundaries = set()
        self.transitions = []
        self.last_request_s = -1.0

    @property
    def ctx(self):
        return deepcopy(self._ctx)

    @property
    def plan(self):
        return deepcopy(self._plan)

    @property
    def events(self):
        return deepcopy(self._events)

    def request(self, request_id: str, scene_time_s: float, count=2, source_mode="keyboard"):
        if source_mode not in ("keyboard", "replay", "real_device"):
            raise ValueError("unlabelled_input_mode")
        if not math.isfinite(scene_time_s) or not 0 <= scene_time_s <= self._ctx.scene["duration_s"]:
            raise ValueError("request_scene_time")
        if request_id in self.requests:
            return {"status": "suppressed", "reason": "duplicate_request"}
        if scene_time_s < self.last_request_s:
            return {"status": "suppressed", "reason": "out_of_order_request"}
        self.last_request_s = scene_time_s
        self.requests.add(request_id)
        if count != 2:
            return {"status": "suppressed", "reason": "single_triple_amplitude_disabled"}
        delta = motion_direction(self._ctx, self._plan, scene_time_s)
        if not delta:
            return {"status": "suppressed", "reason": "stationary_ambiguous_or_uncovered_world_z"}
        c = self._ctx.composition
        bar = int(c["ppq"]*4*c["meter"][0]/c["meter"][1])
        boundaries = [t for t in range(bar, c["length_ticks"], bar) if tick_seconds(c, t) >= scene_time_s]
        if not boundaries:
            return {"status": "suppressed", "reason": "no_remaining_approved_boundary"}
        boundary = boundaries[0]
        if boundary in self.boundaries:
            return {"status": "suppressed", "reason": "boundary_already_queued"}
        to_pc = (self.tonic+delta) % 12
        if not any(t["from_pc"] == self.tonic and t["signed_semitones"] == delta for t in self._plan["transitions"]):
            return {"status": "suppressed", "reason": "transition_not_approved"}
        changed = deepcopy(self._events)
        boundary_s = tick_seconds(c, boundary)
        for e in changed:
            if e["midi_pitch"] is None:
                continue
            if e["resolved_time_s"] < boundary_s < e["resolved_time_s"]+e["duration_s"]:
                # Split sustained pitched voices so no old harmony rings into the new key.
                tail = deepcopy(e)
                tail.update(id=e["id"]+f":mod:{boundary}", start_tick=boundary,
                            duration_ticks=max(1, e["start_tick"]+e["duration_ticks"]-boundary), resolved_time_s=boundary_s,
                            duration_s=e["resolved_time_s"]+e["duration_s"]-boundary_s)
                e["duration_ticks"] = max(1, boundary-e["start_tick"])
                e["duration_s"] = boundary_s-e["resolved_time_s"]
                changed.append(tail)
            if e["resolved_time_s"] >= boundary_s:
                e["midi_pitch"] = bounded_pitch(e["midi_pitch"]+delta, self._plan["register_min"], self._plan["register_max"])
        # At the boundary: explicit new dominant then tonic in the prepared bass/harmony lanes.
        # Existing notes are revoiced, not added, so the preapproved voice budget stays fixed.
        arrival_s = tick_seconds(c, boundary+c["ppq"])
        tonic_intervals = [0, 3 if c["key_map"][0]["mode"] == "minor" else 4, 7]
        for e in changed:
            if e["midi_pitch"] is None or e["resolved_time_s"] < boundary_s:
                continue
            if e["lane_id"] == "bass" or e["lane_id"].startswith("harmony-"):
                if e["resolved_time_s"] < tick_seconds(c, boundary+bar):
                    root_pc = (to_pc+7) % 12 if e["resolved_time_s"] < arrival_s else to_pc
                    intervals = [0, 4, 7] if e["resolved_time_s"] < arrival_s else tonic_intervals
                    interval = intervals[int(e["lane_id"][-1])] if e["lane_id"].startswith("harmony-") else 0
                    e["midi_pitch"] = bounded_pitch((e["midi_pitch"]//12)*12+root_pc+interval, self._plan["register_min"], self._plan["register_max"])
                    e["phrasing"] = "new-dominant" if e["resolved_time_s"] < arrival_s else "new-tonic-arrival"
        # Split the prepared dominant sustain into an explicit tonic arrival when no onset exists.
        for e in list(changed):
            if e["phrasing"] == "new-dominant" and e["resolved_time_s"] < arrival_s < e["resolved_time_s"]+e["duration_s"]:
                tail = deepcopy(e)
                interval = tonic_intervals[int(e["lane_id"][-1])] if e["lane_id"].startswith("harmony-") else 0
                tail.update(id=e["id"]+":arrival", start_tick=boundary+c["ppq"], duration_ticks=e["start_tick"]+e["duration_ticks"]-boundary-c["ppq"],
                            resolved_time_s=arrival_s, duration_s=e["resolved_time_s"]+e["duration_s"]-arrival_s,
                            midi_pitch=bounded_pitch((e["midi_pitch"]//12)*12+to_pc+interval, self._plan["register_min"], self._plan["register_max"]), phrasing="new-tonic-arrival")
                e["duration_ticks"] = boundary+c["ppq"]-e["start_tick"]
                e["duration_s"] = arrival_s-e["resolved_time_s"]
                changed.append(tail)
        changed.sort(key=lambda e: (e["resolved_time_s"], e["id"]))
        validate_event_budget(changed, self._plan, self._policy)
        self._events = changed
        self.boundaries.add(boundary)
        self.tonic = to_pc
        result = {"status": "prepared" if self._approved else "preview_only", "source_mode": source_mode, "boundary_tick": boundary, "signed_semitones": delta,
                  "tonic_pc": to_pc, "mode": c["key_map"][0]["mode"], "policy_id": self._plan["motion_policy"]["id"],
                  "plan_hash": self._plan_hash, "audition_status": "AUDITION_PENDING"}
        self.transitions.append(result)
        return result


class ApprovedSession(TransitionPreview):
    """Exact approval is required to construct a performance preparation session."""
    def __init__(self, payload, approval, ctx, policy=Policy(), brief="Original blues/ragtime swing; restrained bossa accompaniment"):
        plan = approved_payload(payload, approval, [ctx.scene_hash, ctx.composition_hash])
        super().__init__(plan, ctx, policy, brief)
        self._plan_hash = hashlib.sha256(payload).hexdigest()
        self._approved = True
