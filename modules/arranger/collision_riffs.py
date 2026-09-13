"""Original, editable 12-bar contact call/response; opt-in beside legacy scores."""

from copy import deepcopy
import hashlib
from pathlib import Path

from scenescore.contracts import validate
from .core import Context, Policy, baseline, digest, encoded, note_event, validate_event_budget

VERSION = "collision-riffs-1"
LEADS = {"guitar": "guitar_fingerstyle_v1", "vibraphone": "vibraphone_soft_v1"}
# Beat, MIDI pitch, occupied beats. Rests and answers are written, not cloned per object.
PHRASES = [
    [(0, 60, 0.5), (0.5, 63, 0.5), (1, 64, 0.5), (1.5, 67, 1), (3, 69, 0.5), (3.5, 67, 0.4)],
    [(0.5, 65, 0.5), (1, 68, 0.5), (1.5, 72, 1), (3, 70, 0.5)],
    [(0, 67, 0.5), (0.5, 64, 0.5), (1, 63, 0.5), (2, 60, 1.4)],
    [(1, 62, 0.5), (1.5, 63, 0.5), (2, 64, 0.5), (3, 67, 0.6)],
    [(0, 65, 0.5), (0.5, 68, 0.5), (1, 69, 0.5), (1.5, 72, 0.8), (3, 74, 0.5)],
    [(0.5, 75, 0.5), (1, 72, 0.5), (2, 69, 0.5), (2.5, 68, 0.5), (3, 65, 0.6)],
    [(0, 64, 0.5), (0.5, 67, 0.5), (1, 72, 1), (2.5, 70, 0.5)],
    [(0, 69, 0.5), (0.5, 73, 0.5), (1.5, 76, 0.6), (3, 73, 0.5)],
    [(0.5, 74, 0.5), (1, 72, 0.5), (1.5, 69, 0.5), (2.5, 65, 0.8)],
    [(0, 71, 0.5), (0.5, 69, 0.5), (1, 67, 0.5), (2, 65, 0.5), (2.5, 62, 0.5)],
    [(0, 60, 0.5), (0.5, 63, 0.5), (1, 64, 0.5), (1.5, 67, 0.7), (3, 64, 0.5)],
    [(0, 62, 0.5), (0.5, 59, 0.5), (1, 60, 1.6)],
]
ROOTS = [0, 5, 0, 0, 5, 5, 0, 9, 2, 7, 0, 0]
# Written responses in the hook's gaps; all attacks use the same once-swung tick clock.
PIANO_BEATS = [
    (2.5,),
    (0, 2.5, 3.5),
    (1.5, 3.5),
    (0, 2.5),
    (2.5, 3.5),
    (0, 1.5),
    (2, 3.5),
    (1, 2.5),
    (0, 2, 3.5),
    (1.5, 3.5),
    (2.5, 3.5),
    (3,),
]
PIANO_VOICINGS = [
    (52, 58, 62),
    (51, 57, 60),
    (52, 58, 62),
    (52, 58, 62),
    (51, 57, 60),
    (51, 57, 60),
    (52, 58, 62),
    (49, 55, 59),
    (53, 57, 60),
    (53, 57, 59),
    (52, 58, 62),
    (52, 57, 60),
]


def arrange(source, lead="guitar"):
    if lead not in LEADS:
        raise ValueError("unknown_riff_instrument")
    # This edition targets the 30 s Jam demo. Other clocks require a separately reviewed form.
    if source["scene"]["duration_s"] != 30 or source.get("playback_window") or source.get("music_vertical"):
        raise ValueError("riff_edition_requires_30_second_legacy_demo")
    duet = lead == "guitar"
    b = deepcopy(source)
    c = b["composition"]
    c.update(
        id="pocket_workshop_v1",
        title="Pocket Workshop",
        catalog_version=1,
        length_ticks=46080,
        ppq=960,
        tempo_map=[{"tick": 0, "bpm": 96}],
        swing_ratio=2 / 3,
        creative_traits=[
            "Original 12-bar guitar hook with displaced answers and intentional rests.",
            "Light blues swing; restrained offbeat accompaniment; no borrowed music.",
            "Contact replies preserve object voices; scene onsets are never quantized.",
        ],
    )
    c["provenance"].update(
        creator=VERSION, tool_version=VERSION, config_hash=digest(PHRASES), input_hashes=[source["composition_hash"]]
    )
    c["notes"] = [
        dict(
            start_tick=bar * 3840 + round(beat * 960),
            duration_ticks=round(length * 960),
            midi_pitch=pitch,
            velocity=92 if i == 0 else 80 + (i % 3) * 4,
            articulation="ring" if length >= 0.7 else "palm_mute",
            swingable=True,
        )
        for bar, phrase in enumerate(PHRASES)
        for i, (beat, pitch, length) in enumerate(phrase)
    ]
    c["harmony"] = [
        dict(
            start_tick=i * 3840,
            duration_ticks=3840,
            root_pc=root,
            intervals_semitones=[0, 3, 7, 10] if i == 8 else [0, 4, 7, 9] if i == 11 else [0, 4, 7, 10],
            quality="m7" if i == 8 else "6" if i == 11 else "7",
        )
        for i, root in enumerate(ROOTS)
    ]
    if duet:
        c["id"] = "pocket_workshop_piano_guitar_v2"
        c["catalog_version"] = 2
        c["creative_traits"].append(
            "Piano guide tones answer guitar rests, with shared swing and quiet contact windows."
        )
        for h in c["harmony"]:
            if h["quality"] == "7" and h["root_pc"] in (0, 9, 7):
                h["intervals_semitones"].append(14)
                h["quality"] = "9"
    ctx = Context(b["scene"], b["states"], b["interactions"], c, b["groove"])
    plan = baseline(ctx)
    policy = Policy(gain_db=-3)
    events = []
    owner = {x["object_id"]: x["motif_id"] for x in plan["motif_owners"]}
    projectile = next((o for o in ctx.objects if o.endswith(":projectile")), ctx.objects[0])
    instrument = LEADS[lead]

    def note(ident, obj, lane, tick, duration, pitch, velocity, articulation="ring", swing=True, bass=False):
        e = note_event(
            plan,
            VERSION + ":" + ident,
            obj,
            lane,
            "bass" if bass else "piano",
            tick,
            duration,
            pitch,
            velocity,
            articulation,
            c,
            policy,
            swing,
        )
        if not bass:
            e.update(instrument_id=instrument, timbre_id=instrument)
        events.append(e)
        return e

    for i, n in enumerate(c["notes"]):
        note(
            "lead:" + str(i),
            projectile,
            owner[projectile],
            n["start_tick"],
            n["duration_ticks"],
            n["midi_pitch"],
            n["velocity"],
            n["articulation"],
        )
    for bar, h in enumerate(c["harmony"]):
        # Two-beat bass and sparse shell voicings leave the hook exposed.
        for beat, interval in [(0, 0), (2, 7)]:
            note(
                f"bass:{bar}:{beat}",
                None,
                "bass",
                bar * 3840 + beat * 960,
                820,
                36 + h["root_pc"] + interval,
                100,
                "light_detached",
                False,
                True,
            )["dynamics_db"] = 3
        for beat in [] if duet else ([1.5] if bar == 11 else [1.5, 3]):
            for i, interval in enumerate([h["intervals_semitones"][1], h["intervals_semitones"][3]]):
                e = note(
                    f"comp:{bar}:{beat}:{i}",
                    None,
                    "comp-" + str(i),
                    round((bar * 4 + beat) * 960),
                    360,
                    48 + h["root_pc"] + interval,
                    50,
                    "palm_mute",
                )
                e["dynamics_db"] = -8
    for bar in range(12):
        for i, n in enumerate(b["groove"]["events"]):
            e = note_event(
                plan,
                f"{VERSION}:brush:{bar}:{i}",
                None,
                "brushes",
                "brushes",
                bar * 3840 + n["start_tick"],
                n["duration_ticks"],
                60,
                n["velocity"],
                n["technique"],
                c,
                policy,
                n["swingable"],
            )
            e.update(event_type="brush", midi_pitch=None, dynamics_db=-15)
            events.append(e)
    contacts = sorted(
        (e for e in b["interactions"] if e["event_type"] == "contact_onset"), key=lambda e: (e["onset_s"], e["id"])
    )
    refs = []
    for contact in contacts:
        obj = next((o for o in reversed(contact["pair"]) if o != projectile and o in owner), projectile)
        idx = ctx.objects.index(obj)
        at = contact["onset_s"]
        intensity = min(1, abs(contact["relative_normal_speed_m_s"] or 0) / 0.2)
        e = deepcopy(events[0])
        e.update(
            id="foley:" + contact["id"],
            object_id=obj,
            lane_id="contact:" + contact["pair_id"],
            event_type="foley",
            instrument_id="wood_contact_v1",
            timbre_id=["wood-low", "wood-mid", "wood-high"][idx % 3],
            start_tick=None,
            duration_ticks=None,
            resolved_time_s=at,
            scene_time_s=at,
            duration_s=min(0.2, 30 - at),
            midi_pitch=None,
            velocity=round(60 + 35 * intensity),
            dynamics_db=0,
            articulation="contact_knock",
            phrasing="exact-scene-time",
            swing_applied=False,
            swing_application_count=0,
        )
        events.append(e)
        bar = min(11, int(at / 2.5))
        root = ROOTS[bar]
        reply_ids = []
        # Distinct fixed object contour, harmonious with the current bar. Exact onset + written delay.
        contour = [0, 4, 7] if idx % 2 else [7, 4, 0]
        for j, interval in enumerate(contour):
            start = at + j * 0.125
            reply = note(
                f"reply:{contact['id']}:{j}",
                obj,
                owner[obj],
                round(start * 1536),
                144,
                60 + root + interval,
                round(76 + 15 * intensity) - j * 5,
                "ring",
                False,
            )
            reply.update(
                resolved_time_s=start,
                duration_s=0.18,
                scene_time_s=start,
                phrasing="contact-answer",
                ornament="contact-reply:" + contact["id"],
            )
            reply_ids.append(reply["id"])
        refs.append(
            dict(
                interaction_id=contact["id"],
                onset_s=at,
                foley_id=e["id"],
                reply_ids=reply_ids,
                method=contact["method"],
                physical_impact=contact["physical_impact"],
                interpretation="Authored scene cue; wood color is artistic, not measured acoustics.",
            )
        )
    piano_groups = []
    if duet:
        for bar, beats in enumerate(PIANO_BEATS):
            for beat in beats:
                tick = round((bar * 4 + beat) * 960)
                group = []
                for voice_index, pitch in enumerate(PIANO_VOICINGS[bar]):
                    e = note_event(
                        plan,
                        f"piano-duet:{bar}:{beat}:{voice_index}",
                        None,
                        f"piano-comp-{voice_index}",
                        "piano",
                        tick,
                        min(960, 46080 - tick),
                        pitch,
                        61 if bar == 11 else 55,
                        "soft_comp",
                        c,
                        policy,
                        True,
                    )
                    e.update(
                        instrument_id="piano_felt_comp_v1",
                        timbre_id="piano_felt_comp_v1",
                        dynamics_db=-5 if bar == 11 else -6,
                        phrasing="piano-answer-in-guitar-rest",
                    )
                    start = e["resolved_time_s"]
                    end = min(e["resolved_time_s"] + e["duration_s"], (bar + 1) * 2.5)
                    # A written rest, including the entire piano tail, exposes each contact reply.
                    for contact in contacts:
                        left, right = contact["onset_s"] - 0.06, contact["onset_s"] + 0.5
                        if left <= start < right:
                            end = start
                            break
                        if start < left < end:
                            end = left
                    if end - start < 0.18:
                        continue
                    e["duration_s"] = end - start
                    whole, phase = divmod(end * 1536, 960)
                    end_tick = whole * 960 + (phase * 0.75 if phase <= 640 else 480 + (phase - 640) * 1.5)
                    e["duration_ticks"] = max(1, round(end_tick - tick))
                    group.append(e)
                if group:
                    events.extend(group)
                    piano_groups.append(
                        dict(
                            bar=bar,
                            beat=beat,
                            start_tick=tick,
                            onset_s=group[0]["resolved_time_s"],
                            event_ids=[e["id"] for e in group],
                        )
                    )

    # Carve space around each reply. Preserve the full original lead in CompositionSpec.
    projected = []
    for e in events:
        if e["lane_id"] == owner[projectile] and e["ornament"] is None:
            for contact in contacts:
                start, end = contact["onset_s"] - 0.04, contact["onset_s"] + 0.5
                if start <= e["resolved_time_s"] < end:
                    break
                if e["resolved_time_s"] < start < e["resolved_time_s"] + e["duration_s"]:
                    e["duration_s"] = start - e["resolved_time_s"]
                    e["duration_ticks"] = max(1, round(e["duration_s"] * 1536))
            else:
                projected.append(e)
            continue
        projected.append(e)
    events = sorted(projected, key=lambda e: (e["resolved_time_s"], e["id"]))
    for e in events:
        e["duration_s"] = min(e["duration_s"], 30 - e["resolved_time_s"])
    # Binding excludes only plan_id to avoid a plan/content hash cycle; exact source bytes retained.
    content = [{k: v for k, v in e.items() if k != "plan_id"} for e in events]
    content_bytes = encoded(content).decode()
    source_paths = ["modules/arranger/collision_riffs.py", "packages/audio/riff-voices.ts"]
    design = dict(
        version="collision-riffs-2" if duet else VERSION,
        voice_version="collision-riff-voices-2",
        lead=lead,
        title="Pocket Workshop",
        events_content_sha256=hashlib.sha256(content_bytes.encode()).hexdigest(),
        source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_paths},
        contact_replies=refs,
        final_fade_s=0.01,
        default_gain_db=-9,
        label="Draft · piano and guitar duet · audition pending"
        if lead == "guitar"
        else "Draft · original melody / vibraphone variation · audition pending",
        original_bundle_sha256=digest(source),
        original_events_sha256=source["events_sha256"],
    )
    if duet:
        design["piano_accompaniment"] = dict(
            version="piano-guitar-comp-1",
            instrument_id="piano_felt_comp_v1",
            clock="shared-score-ticks",
            swing_application_count=1,
            groups=piano_groups,
            contact_rest_before_s=0.06,
            contact_rest_after_s=0.5,
        )
    design_bytes = encoded(design).decode()
    design_hash = digest(design)
    plan["id"] = "plan-riffs-" + design_hash[:20]
    plan["palette_ids"] = [instrument, "bass_pluck_v1", "brush_noise_v1", "wood_contact_v1"]
    if duet:
        plan["palette_ids"].append("piano_felt_comp_v1")
    plan["provenance"].update(config_hash=design_hash, input_hashes=[ctx.scene_hash, ctx.composition_hash, design_hash])
    plan["uncertainties"] = [
        "AUDITION_PENDING. Original synthesized instrument approximations.",
        "Legacy animation cues remain authored; this score does not certify physical impact.",
    ]
    for e in events:
        e["plan_id"] = plan["id"]
    validate(plan)
    validate(c)
    validate_event_budget(events, plan, policy)
    b.update(
        id=source["id"] + ("-guitar-piano-v2" if duet else "-" + lead),
        composition_hash=ctx.composition_hash,
        events=events,
        events_sha256=digest(events),
        events_bytes=encoded(events).decode(),
        source_events_bytes=encoded(events).decode(),
        composition_input_bytes=encoded({"composition": c, "groove": b["groove"]}).decode(),
        plan_bytes=encoded(plan).decode(),
        plan_sha256=digest(plan),
        sound_design=design,
        sound_design_bytes=design_bytes,
        sound_design_sha256=design_hash,
        sound_design_event_bytes=content_bytes,
        approval=None,
        audition_status="AUDITION_PENDING",
        label=design["label"],
    )
    return b
