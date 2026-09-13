"""Bounded data-only arrangement compiler against frozen contract 0.1."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
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
    role_supplement: dict | None = None
    playback_policy: dict | None = None
    music_handoff_binding: dict | None = None

    def __post_init__(self):
        if self.music_handoff_binding is not None:
            binding=self.music_handoff_binding
            if (binding.get('version')!='scene-music-input-binding-1' or
                    any(not isinstance(binding.get(k),str) or not re.fullmatch(r'[0-9a-f]{64}',binding[k])
                        for k in ('handoff_sha256','features_sha256','handoff_index_sha256'))):
                raise ValueError('invalid_music_handoff_binding')
        if self.role_supplement is not None:
            known={o['object_id'] for o in self.scene.get('objects',[])}
            scored=self.role_supplement.get('scored_object_ids',[])
            if not scored or len(set(scored))!=len(scored) or not set(scored)<=known:
                raise ValueError('invalid_scored_object_roles')
            if self.role_supplement.get('scene_id')!=self.scene.get('id'):
                raise ValueError('stale_object_roles')
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
        return sorted(self.role_supplement['scored_object_ids'] if self.role_supplement is not None
                      else (o["object_id"] for o in self.scene["objects"]))

    @property
    def scene_inputs(self):
        inputs={"scene": self.scene, "states": sorted(self.states, key=lambda s: s["id"]),
                "interactions": sorted(self.interactions, key=lambda s: s["id"])}
        if self.role_supplement is not None:
            inputs['role_supplement']=self.role_supplement
        if self.playback_policy is not None:
            inputs['playback_policy']=self.playback_policy
        if self.music_handoff_binding is not None:
            inputs['music_handoff_binding']=self.music_handoff_binding
        return inputs

    @property
    def scene_hash(self):
        return digest(self.scene_inputs)

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
        if ctx.role_supplement is not None and (interaction['event_type']!='contact_onset' or
                interaction['id'] not in ctx.role_supplement.get('validated_contact_ids',[])):
            continue
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


# Additive music vertical. The canonical/legacy compiler above is intentionally unchanged.
VERTICAL_VERSION = 'arranger-music-vertical-1'
VERTICAL_LANES = {
    ('approach', 'ornament'): (0, 1), ('approach', 'tension'): (0, .8), ('approach', 'register'): (0, 5),
    ('near_miss', 'tension'): (.4, 1), ('near_miss', 'phrasing'): (0, 1), ('near_miss', 'dynamics'): (-6, 0),
    ('separation', 'dynamics'): (-12, 0), ('separation', 'register'): (-7, 0), ('separation', 'ornament'): (0, .3),
    ('contact_onset', 'accent'): (0, 1), ('contact_onset', 'timbre'): (0, 1),
    ('contact_sustain', 'timbre'): (0, 1), ('contact_sustain', 'dynamics'): (-9, -3),
    ('contact_release', 'phrasing'): (0, 1), ('contact_release', 'dynamics'): (-6, 0),
    ('collision', 'accent'): (0, 1), ('collision', 'timbre'): (0, 1),
    ('asymmetric_rebound', 'accent'): (0, 1), ('asymmetric_rebound', 'register'): (0, 12),
    ('asymmetric_rebound', 'ornament'): (0, .7),
}


def _vertical_configuration(ctx, supplied):
    config = {'articulation_enabled': True, 'dynamics_enabled': True, 'ornaments_enabled': True,
              'hold_beats': 1.0, 'max_quantization_s': .75, 'max_changed_note_fraction': .05,
              'max_changed_lead_fraction': .1, 'focus_object_id': ctx.objects[0]}
    supplied = {} if supplied is None else deepcopy(supplied)
    if set(supplied)-config.keys():
        raise ValueError('unknown_vertical_mapping_configuration')
    config.update(supplied)
    for key in ('articulation_enabled', 'dynamics_enabled', 'ornaments_enabled'):
        if type(config[key]) is not bool:
            raise ValueError('invalid_vertical_boolean')
    bounds = {'hold_beats': (1, 2), 'max_quantization_s': (0, 1),
              'max_changed_note_fraction': (0, .05), 'max_changed_lead_fraction': (0, .1)}
    for key, (lo, hi) in bounds.items():
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('invalid_vertical_mapping_range:' + key)
    if config['focus_object_id'] not in ctx.objects:
        raise ValueError('unknown_vertical_focus_object')
    return config


def _vertical_musical(events):
    """Remove only circular plan/provenance fields for the plan's content binding."""
    return [{key: value for key, value in event.items() if key not in ('plan_id', 'provenance')}
            for event in sorted(events, key=lambda e: (e['resolved_time_s'], e['id']))]


def _vertical_source(ctx, policy, variation):
    from modules.music.events import resolve_events
    events = resolve_events(ctx.composition, ctx.groove, plan_id='music-vertical-source',
                            object_id=ctx.objects[0], variation=variation)
    owner_index, slots = 0, {}
    for event in events:
        event['dynamics_db'] = policy.gain_db
        if event['lane_id'] == 'object_motif':
            event['object_id'] = ctx.objects[owner_index % len(ctx.objects)]
            owner_index += 1
        elif event['articulation'] == 'soft_comp':
            key = (event['start_tick'], event['duration_ticks'], event['resolved_time_s'])
            slots.setdefault(key, []).append(event)
    for group in slots.values():
        if len(group) != 3:
            raise ValueError('vertical_requires_three_authored_comping_voices')
        for index, event in enumerate(sorted(group, key=lambda e: (e['midi_pitch'], e['id']))):
            event['lane_id'] = f'harmony-{index}'
    return events


def _causal_pair_closing(ctx, pair, at, reference_speed):
    from modules.blender.geometry import normal_speed
    rows = []
    for oid in pair:
        rows.append({s['scene_time_s']: s for s in ctx.states
                     if s['object_id'] == oid and s['scene_time_s'] <= at})
    times = sorted(rows[0].keys() & rows[1].keys())
    max_gap = ctx.scene['fps_base']/ctx.scene['fps']
    if len(times) < 2 or at-times[-1] > max_gap+1e-9 or times[-1]-times[-2] > max_gap+1e-9:
        return None
    before, now = times[-2:]
    points = [rows[j][t]['transform']['position_m'] for j, t in [(0, before), (0, now), (1, before), (1, now)]]
    normal = normal_speed(*points, now-before)
    return None if normal is None else min(1., max(0., -normal/reference_speed))


def _vertical_chord(ctx, seconds):
    for chord in reversed(ctx.composition['harmony']):
        if tick_seconds(ctx.composition, chord['start_tick']) <= seconds+1e-9:
            return chord
    raise ValueError('vertical_harmony_out_of_coverage')


def _vertical_beat_end(ctx, start, beats):
    """Integrate beats over the authored tempo map; no assumed global tempo."""
    tempos = ctx.composition['tempo_map']
    remaining, cursor = beats, start
    for index, tempo in enumerate(tempos):
        begin = tick_seconds(ctx.composition, tempo['tick'])
        end = tick_seconds(ctx.composition, tempos[index+1]['tick']) if index+1 < len(tempos) else ctx.scene['duration_s']
        if end <= cursor or begin > cursor+1e-9:
            continue
        available = (end-cursor)*tempo['bpm']/60
        if remaining <= available+1e-9:
            return cursor+remaining*60/tempo['bpm']
        remaining -= available
        cursor = end
    raise ValueError('near_miss_one_beat_hold_exceeds_media')


def _vertical_control_values(feature, driver, mappings):
    # Reuse the original bounded linear curve and its mapping record shape.
    return {mapping['lane']: curve({'mappings': [mapping]}, feature, driver)
            for mapping in mappings if mapping['feature'] == feature}


def _vertical_controls(ctx, semantics, source, config, policy):
    mappings = [{'feature': feature, 'lane': lane, 'input_min': 0., 'input_max': 1.,
                 'output_min': lo, 'output_max': hi} for (feature, lane), (lo, hi) in VERTICAL_LANES.items()]
    for mapping in mappings:
        if (mapping['feature'], mapping['lane']) == ('asymmetric_rebound', 'register'):
            mapping.update(input_min=1., input_max=16.)
    controls, holds, suppressed = [], [], deepcopy(semantics['suppressed'])
    cadence = ctx.scene['fps_base']/ctx.scene['fps']
    for episode in semantics['events']:
        feature, driver = episode['event_type'], episode['driver']
        if driver is None:
            continue
        start, end = episode['onset_s'], episode['onset_s']+episode['duration_s']
        if feature == 'near_miss':
            if episode.get('certified_no_tunnelling') is not True or episode.get('minimum_s') is None:
                suppressed.append({'source_event_id': episode['source_event_id'], 'reason': 'uncertified_near_miss'})
                continue
            start = episode['minimum_s']
            end = _vertical_beat_end(ctx, start, config['hold_beats'])
            chord = _vertical_chord(ctx, start)
            thirds = [i for i in chord['intervals_semitones'] if i % 12 in (3, 4)]
            holds.append({'id': episode['id']+':hold', 'source_event_id': episode['source_event_id'],
                          'start_s': start, 'end_s': end, 'root_pc': chord['root_pc'],
                          'withheld_pitch_classes': sorted({(chord['root_pc']+i) % 12 for i in thirds}),
                          'reason': 'near_miss_withheld_resolution', 'hold_beats': config['hold_beats'],
                          'pair_id': episode['pair_id'], 'no_accent': True, 'no_foley': True, 'no_key_change': True})
        end = min(ctx.scene['duration_s'], max(end, start+cadence))
        if end <= start:
            suppressed.append({'source_event_id': episode['source_event_id'], 'reason': 'event_has_no_media_coverage'})
            continue
        basic = {'id': episode['id']+':control', 'source_event_id': episode['source_event_id'],
                 'feature': feature, 'pair_id': episode['pair_id'], 'object_ids': list(episode['pair']),
                 'start_s': start, 'end_s': end, 'driver': driver,
                 'values': _vertical_control_values(feature, driver, mappings),
                 'intent': feature, 'source_slot_ids': [], 'quantization_delay_s': None}
        if feature == 'asymmetric_rebound':
            basic.update(rebounding_object_id=episode['rebounding_object_id'], anchor_object_id=episode['anchor_object_id'],
                         area_ratio=episode['area_ratio'], speed_retention=episode['speed_retention'],
                         chain_index=episode['chain_index'], mass_inferred=False, restitution_claimed=False)
            area_curve = next(mapping for mapping in mappings if
                              (mapping['feature'], mapping['lane']) == ('asymmetric_rebound', 'register'))
            basic['values']['register'] = curve({'mappings': [area_curve]}, feature, episode['area_ratio'])
        if feature == 'approach':
            # Resolve only at existing source slots and only from evaluated samples
            # at/before each slot. Neither future minimum scalar nor gap is used.
            for note in source:
                at = note['resolved_time_s']
                if note['event_type'] != 'note' or not start <= at < end:
                    continue
                if note['object_id'] not in (None, *episode['pair']):
                    continue
                causal = _causal_pair_closing(ctx, episode['pair'], at, semantics['config']['approach_ref_speed_m_s'])
                if causal is None:
                    suppressed.append({'source_event_id': episode['source_event_id'], 'source_slot_id': note['id'],
                                       'reason': 'causal_pair_motion_out_of_coverage', 'fallback': 'unmodified_score'})
                    continue
                controls.append({**basic, 'id': basic['id']+':'+note['id'], 'start_s': at,
                                 'end_s': min(end, at+note['duration_s']), 'driver': causal,
                                 'values': _vertical_control_values(feature, causal, mappings),
                                 'source_slot_ids': [note['id']], 'motion_sample_latest_s': max(
                                     s['scene_time_s'] for s in ctx.states if s['object_id'] in episode['pair'] and s['scene_time_s'] <= at)})
        else:
            controls.append(basic)
    controls.sort(key=lambda row: (row['start_s'], row['feature'], row['id']))
    return {'document_type': 'SceneScoreMotionControlTrack', 'document_version': 1,
            'clock': 'scene', 'epoch': ctx.scene['id'], 'duration_s': ctx.scene['duration_s'],
            'config': config, 'mappings': mappings, 'events': controls, 'suppressed': suppressed}, holds


def _vertical_realize(ctx, source, track, holds, config, seed):
    from modules.music.ornament import TransformBudgets, TransformRequest, apply_transforms
    notes = [event for event in source if event['event_type'] == 'note']
    lookup = {event['id']: event for event in notes}
    requests, dynamics, register, diagnostics = {}, {}, {}, []
    decorated = set()
    changed_limit = math.floor(len(notes)*config['max_changed_note_fraction'])

    def request(note, kind, control, **parameters):
        key = (note['id'], kind)
        # Later causal controls win at the same source slot; iteration is stable.
        requests[key] = TransformRequest(note['id'], kind, **parameters)
        if note['id'] not in control['source_slot_ids']:
            control['source_slot_ids'].append(note['id'])

    def first_slot(control, owner=None):
        candidates = [event for event in notes if event['resolved_time_s'] >= control['start_s']-1e-9
                      and event['resolved_time_s']-control['start_s'] <= config['max_quantization_s']+1e-9
                      and (event['object_id'] == owner if owner is not None else
                           event['object_id'] in control['object_ids'])]
        if not candidates and owner is None:
            candidates = [event for event in notes if event['lane_id'].startswith('harmony-')
                          and control['start_s'] <= event['resolved_time_s'] <= control['start_s']+config['max_quantization_s']]
        if not candidates:
            diagnostics.append({'source_event_id': control['source_event_id'], 'reason': 'no_existing_source_slot_in_window'})
            return None
        event = min(candidates, key=lambda e: (e['resolved_time_s'], e['id']))
        delay = event['resolved_time_s']-control['start_s']
        if control['quantization_delay_s'] is None:
            control['quantization_delay_s'] = delay
        control.setdefault('source_slot_delays_s', {})[event['id']] = delay
        return event

    priority = {'approach': 0, 'separation': 1, 'contact_sustain': 2, 'contact_release': 3,
                'near_miss': 4, 'contact_onset': 5, 'collision': 5, 'asymmetric_rebound': 6}
    for control in sorted(track['events'], key=lambda row: (row['start_s'], priority[row['feature']], row['id'])):
        feature, driver = control['feature'], control['driver']
        if feature == 'approach':
            note = lookup[control['source_slot_ids'][0]]
            if config['articulation_enabled'] and driver > .01:
                request(note, 'articulation', control, articulation='legato')
        elif feature in ('contact_onset', 'collision', 'asymmetric_rebound'):
            owner = control.get('rebounding_object_id')
            note = first_slot(control, owner)
            if note is None:
                continue
            if config['articulation_enabled']:
                request(note, 'articulation', control, articulation='staccato' if feature != 'asymmetric_rebound' else 'tenuto')
            if feature == 'asymmetric_rebound':
                velocity = max(1, round(note['velocity']*control['speed_retention']*(.8**control['chain_index'])))
                if abs(velocity-note['velocity']) > 32:
                    diagnostics.append({'source_event_id': control['source_event_id'],
                                        'reason': 'rebound_velocity_outside_transform_delta_budget',
                                        'fallback': 'no_rebound_decoration'})
                    continue
                if config['ornaments_enabled'] and len(decorated) < changed_limit:
                    request(note, 'grace', control)
                    decorated.add(note['id'])
                # Explicit separate register/velocity declarations, never coupled
                # to the accepted key-change control or global expression preset.
                shift = round(control['values']['register'])
                register[note['id']] = shift
                request(note, 'velocity', control, velocity_delta=velocity-note['velocity'])
                anchor = first_slot(control, control['anchor_object_id'])
                if anchor is not None and config['articulation_enabled']:
                    request(anchor, 'articulation', control, articulation='staccato')
                    register[anchor['id']] = -12
        elif feature in ('separation', 'contact_sustain', 'contact_release', 'near_miss'):
            for note in notes:
                at = note['resolved_time_s']
                if not control['start_s'] <= at < control['end_s']:
                    continue
                if note['object_id'] not in (None, *control['object_ids']):
                    continue
                if config['articulation_enabled']:
                    articulation = 'legato' if feature in ('near_miss', 'contact_sustain') else 'detached'
                    request(note, 'articulation', control, articulation=articulation)
                if config['dynamics_enabled']:
                    progress = (at-control['start_s'])/(control['end_s']-control['start_s'])
                    offset = -12*driver*progress if feature == 'separation' else (
                        -6*driver if feature in ('near_miss', 'contact_release') else control['values']['dynamics'])
                    dynamics[note['id']] = min(dynamics.get(note['id'], 0.), offset)
    # No added decorative attack may coincide with an unresolved-harmony hold.
    for key, item in list(requests.items()):
        note = lookup[item.event_id]
        if item.kind == 'grace' and any(note['resolved_time_s'] < hold['end_s'] and
                                        note['resolved_time_s']+note['duration_s'] > hold['start_s'] for hold in holds):
            del requests[key]
            diagnostics.append({'source_slot_id': note['id'], 'reason': 'ornament_suppressed_during_near_miss_hold'})
    budgets = TransformBudgets()
    # Style lanes execute before decorations. Applying velocity after a grace
    # would correctly be rejected by node03's existing-ornament guard.
    styles = [item for item in requests.values() if item.kind in ('articulation', 'velocity')]
    decorations = [item for item in requests.values() if item.kind not in ('articulation', 'velocity')]
    styled = apply_transforms(source, styles, ctx.composition, seed=seed, budgets=budgets)
    transformed = apply_transforms(styled.events, decorations, ctx.composition, seed=seed, budgets=budgets)
    events = transformed.events
    explicit = []
    for event in events:
        if event['event_type'] != 'note':
            continue
        parent_id = event['id'].split(':music-ornament-1:')[0]
        if parent_id in dynamics:
            event['dynamics_db'] = max(-48., min(-3., event['dynamics_db']+dynamics[parent_id]))
            explicit.append({'event_id': event['id'], 'lane': 'dynamics', 'offset_db': dynamics[parent_id]})
        if parent_id in register:
            event['midi_pitch'] = bounded_pitch(event['midi_pitch']+register[parent_id], 28, 96)
            explicit.append({'event_id': event['id'], 'lane': 'register', 'semitones': register[parent_id]})
    return events, {'transform': transformed.audit, 'style_transform': styled.audit, 'explicit_lane_changes': explicit,
                    'suppressed': diagnostics, 'budgets': asdict(budgets)}


def _vertical_withhold_thirds(events, holds):
    """Declared source-slot omission/splitting, with no new attack at a minimum."""
    output, edits = [], []
    for event in events:
        if event['event_type'] != 'note':
            output.append(event)
            continue
        start, end = event['resolved_time_s'], event['resolved_time_s']+event['duration_s']
        pieces = [(start, end)]
        causes = []
        for hold in holds:
            if event['midi_pitch'] % 12 not in hold['withheld_pitch_classes']:
                continue
            if start >= hold['end_s'] or end <= hold['start_s']:
                continue
            causes.append(hold['id'])
            remaining = []
            for left, right in pieces:
                if right <= hold['start_s'] or left >= hold['end_s']:
                    remaining.append((left, right))
                else:
                    if left < hold['start_s']:
                        remaining.append((left, hold['start_s']))
                    if right > hold['end_s']:
                        remaining.append((hold['end_s'], right))
            pieces = remaining
        if not causes:
            output.append(event)
            continue
        kept = []
        for index, (left, right) in enumerate(pieces):
            if right-left < .025:
                continue
            raw_start = event['start_tick']+round(event['duration_ticks']*(left-start)/(end-start))
            raw_end = event['start_tick']+round(event['duration_ticks']*(right-start)/(end-start))
            if raw_end <= raw_start:
                continue
            note = {**deepcopy(event), 'id': event['id'] if not kept else event['id']+f':hold-resume:{index}',
                    'resolved_time_s': left, 'duration_s': right-left, 'start_tick': raw_start,
                    'duration_ticks': raw_end-raw_start, 'phrasing': 'near-miss-third-withheld'}
            kept.append(note)
        output.extend(kept)
        edits.append({'source_slot_id': event['id'], 'hold_ids': causes, 'source_slot_s': [start, end],
                      'retained_intervals_s': [[e['resolved_time_s'], e['resolved_time_s']+e['duration_s']] for e in kept],
                      'method': 'explicit_third_omission_inside_source_slot', 'duration_preserving': False,
                      'unchanged_before_minimum': True, 'envelope_perception': 'AUDITION_PENDING'})
    return sorted(output, key=lambda e: (e['resolved_time_s'], e['id'])), edits


def _vertical_foley(ctx, semantics, policy):
    events = []
    for source in semantics['events']:
        kind, start = source['event_type'], source['onset_s']
        if kind not in ('contact_onset', 'collision', 'contact_sustain', 'contact_release') or source['driver'] is None:
            continue
        duration = min(max(.01, source['duration_s']), ctx.scene['duration_s']-start)
        if duration <= 0:
            continue
        event = base_record('ScoreEvent', 'vertical-foley:'+source['source_event_id'], ctx.scene['provenance'])
        event.update(plan_id='music-vertical-source', object_id=source['pair'][0], lane_id='contact:'+source['pair_id'],
                     event_type='foley', instrument_id=INSTRUMENTS['foley'], start_tick=None, duration_ticks=None,
                     resolved_time_s=start, duration_s=duration, scene_time_s=start, midi_pitch=None,
                     velocity=90 if kind in ('collision', 'contact_onset') else 40, dynamics_db=policy.gain_db,
                     articulation=kind, phrasing='exact-scene-time', ornament=None,
                     timbre_id='contact-bright' if source['driver'] >= .5 else 'contact-soft',
                     swing_applied=False, swing_application_count=0)
        events.append(event)
    return events


def _vertical_identity_audit(source, output, config):
    fields = ('start_tick', 'duration_ticks', 'resolved_time_s', 'duration_s', 'midi_pitch')
    lookup = {event['id']: event for event in output}
    notes = [event for event in source if event['event_type'] == 'note']
    lead = [event for event in notes if event['lane_id'] == 'piano_or_lead']
    changed = [event['id'] for event in notes if event['id'] not in lookup or
               any(event[key] != lookup[event['id']][key] for key in fields)]
    changed_lead = [event['id'] for event in lead if event['id'] in changed]
    if len(changed) > len(notes)*config['max_changed_note_fraction']+1e-9:
        raise ValueError('vertical_source_note_identity_budget')
    if len(changed_lead) > len(lead)*config['max_changed_lead_fraction']+1e-9:
        raise ValueError('vertical_source_lead_identity_budget')
    return {'source_note_count': len(notes), 'changed_note_ids': changed,
            'unchanged_note_fraction': 1-len(changed)/len(notes) if notes else 1.,
            'source_lead_count': len(lead), 'changed_lead_ids': changed_lead,
            'unchanged_lead_fraction': 1-len(changed_lead)/len(lead) if lead else 1.}


def _vertical_density_audit(source, output, composition):
    from collections import Counter
    original_ids = {event['id'] for event in source}
    added = sorted(event['resolved_time_s'] for event in output
                   if event['event_type'] != 'foley' and event['id'] not in original_ids)
    left, maximum = 0, 0
    for right, at in enumerate(added):
        while added[left] <= at-1+1e-9:
            left += 1
        maximum = max(maximum, right-left+1)
    bar_ticks = composition['ppq']*4*composition['meter'][0]//composition['meter'][1]
    maximum_bar = max(Counter(event['start_tick']//bar_ticks for event in output
                              if event['event_type'] != 'foley').values(), default=0)
    if maximum > 12 or maximum_bar > 96:
        raise ValueError('vertical_combined_added_density_budget')
    return {'maximum_added_events_per_second': maximum, 'maximum_music_events_per_bar': maximum_bar,
            'hold_splits_included': True, 'foley_excluded': True}


def validate_vertical_result(result):
    """Validate an offline candidate's exact packet bindings; never grant approval."""
    prov = result['provenance']
    binding = prov['binding']
    payload = result['plan_payload'].encode()
    track = {key: value for key, value in result['control_track'].items() if key != 'provenance'}
    checks = [(encoded(result['plan']), payload),
              (hashlib.sha256(payload).hexdigest(), result['plan_payload_sha256']),
              (digest(binding), prov['binding_sha256']),
              (digest(_vertical_musical(result['source_events'])), binding['source_musical_sha256']),
              (digest(_vertical_musical(result['events'])), binding['mapped_musical_sha256']),
              (digest(result['source_events']), prov['source_events_sha256']),
              (digest(result['events']), prov['mapped_events_sha256']),
              (digest(track), binding['control_track_sha256']),
              (digest(result['holds']), binding['holds_sha256'])]
    if any(actual != expected for actual, expected in checks):
        raise ValueError('stale_vertical_candidate_binding')
    if (prov['binding_sha256'] not in result['plan']['provenance']['input_hashes']
            or result['control_track']['provenance']['plan_payload_sha256'] != result['plan_payload_sha256']):
        raise ValueError('unbound_vertical_plan_or_controls')
    if result['approval'] is not None or result['plan']['review_status'] != 'draft':
        raise ValueError('vertical_compiler_output_cannot_synthesize_approval')
    return result


def compile_vertical_preview(ctx: Context, *, geometry, policy=Policy(), seed=42, variation='base',
                             mapping_config=None,
                             brief='Original blues/ragtime swing; restrained bossa accompaniment'):
    """Compile the opt-in source-preserving music vertical; approval remains null.

    The exact supplied composition/groove (including an explicitly selected ending
    edition) is authoritative. No render, scheduler, network or approval runs here.
    Return data includes the bound canonical plan/payload, source and mapped events,
    separate controls/holds/Foley, and objective audits. Canonical schema 0.1 and
    all legacy compiler behavior remain unchanged.
    """
    from modules.blender.summary import motion_semantics_summary
    from modules.music.ornament import VERSION as ornament_version
    config = _vertical_configuration(ctx, mapping_config)
    duration = tick_seconds(ctx.composition, ctx.composition['length_ticks'])
    if abs(duration-ctx.scene['duration_s']) > 1e-9:
        raise ValueError('vertical_score_scene_duration_mismatch')
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('invalid_vertical_seed')
    semantics = motion_semantics_summary(ctx.scene, ctx.states, ctx.interactions, geometry=geometry)
    source = _vertical_source(ctx, policy, variation)
    track, holds = _vertical_controls(ctx, semantics, source, config, policy)
    mapped, realization = _vertical_realize(ctx, source, track, holds, config, seed)
    mapped, hold_edits = _vertical_withhold_thirds(mapped, holds)
    identity = _vertical_identity_audit(source, mapped, config)
    density = _vertical_density_audit(source, mapped, ctx.composition)
    foley = _vertical_foley(ctx, semantics, policy)
    mapped = sorted([*mapped, *foley], key=lambda e: (e['resolved_time_s'], e['id']))
    binding = {'version': VERTICAL_VERSION, 'ornament_version': ornament_version, 'seed': seed,
               'semantics_sha256': digest(semantics), 'mapping_config': config, 'variation': variation,
               'control_track_sha256': digest(track), 'holds_sha256': digest(holds),
               'source_musical_sha256': digest(_vertical_musical(source)),
               'mapped_musical_sha256': digest(_vertical_musical(mapped)),
               'transform_budgets': realization['budgets']}
    bound_brief = brief+'\n'+VERTICAL_VERSION+' binding '+digest(binding)
    plan = baseline(ctx, policy, bound_brief, seed)
    plan['motion_policy']['focus_object_id'] = config['focus_object_id']
    plan['palette_ids'] = sorted(set(plan['palette_ids']) | {event['instrument_id'] for event in mapped})
    plan['provenance']['input_hashes'].append(digest(binding))
    plan['uncertainties'] = [item for item in plan['uncertainties']
                             if item != 'Objects beyond configured voice budget retain identity but are silent.']
    plan['uncertainties'] += ['Source-preserving music vertical; supplemental control/hold hashes are bound in config.',
                              'Persistent object identities share existing authored motif slots; melodies are not duplicated.',
                              'Source slot quantization is disclosed; fixture rebounds are not hero observations.']
    validate(plan)
    for event in [*source, *mapped, *foley]:
        event['plan_id'] = plan['id']
        validate(event)
        if event['resolved_time_s']+event['duration_s'] > duration+1e-9:
            raise ValueError('vertical_event_past_media')
        if event['instrument_id'] not in plan['palette_ids']:
            raise ValueError('vertical_unknown_palette')
    # Foley has an independent stream and never consumes music voice/rate budget.
    validate_event_budget([event for event in mapped if event['event_type'] != 'foley'], plan, policy)
    protected = [event for event in source if event['event_type'] != 'note']
    if protected != [event for event in mapped if event['event_type'] == 'brush']:
        raise ValueError('vertical_protected_brush_changed')
    payload = encoded(plan)
    provenance = {'version': VERTICAL_VERSION, 'source_mode': 'manual_plan', 'scene_source_mode': ctx.scene['provenance']['source_mode'],
                  'real_device': False, 'replay': False, 'synthetic': ctx.scene['provenance']['source_mode'] == 'synthetic',
                  'cached_gpt': False, 'manual_plan': True, 'keyboard': False,
                  'scene_hash': ctx.scene_hash, 'composition_hash': ctx.composition_hash,
                  'binding': binding, 'binding_sha256': digest(binding), 'bound_brief': bound_brief,
                  'source_events_sha256': digest(source), 'mapped_events_sha256': digest(mapped),
                  'approval': None, 'audition_status': 'AUDITION_PENDING'}
    track['provenance'] = {'binding_sha256': digest(binding), 'plan_payload_sha256': hashlib.sha256(payload).hexdigest()}
    audit = {'identity': identity, 'density': density, 'realization': realization, 'hold_edits': hold_edits,
             'protected_brush_unchanged': True, 'foley_excluded_from_music_budget': True,
             'score_duration_s': duration, 'approval': None, 'audition_status': 'AUDITION_PENDING'}
    result = {'plan': plan, 'plan_payload': payload.decode(), 'plan_payload_sha256': hashlib.sha256(payload).hexdigest(),
            'source_events': source, 'source_with_foley_events': sorted([*source, *foley], key=lambda e: (e['resolved_time_s'], e['id'])),
            'events': mapped, 'foley_events': foley, 'control_track': track, 'holds': holds, 'audit': audit,
            'provenance': provenance, 'duration_s': duration, 'approval': None, 'audition_status': 'AUDITION_PENDING'}
    return validate_vertical_result(result)
