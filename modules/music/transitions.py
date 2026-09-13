"""Frozen harmonic programs prepared outside the accepted-control path.

This module is opt-in and does not alter the legacy arranger. The supplied table
contains pitch classes, so concrete, bounded voice leading is solved once during
preparation. Lookup only returns an existing immutable program. No approval is
created here; both the source and the table still require human audition.
"""
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
from types import MappingProxyType


TABLE_PATH = Path(__file__).parent / 'fixtures' / 'transition-table-v1.json'
TABLE_SHA256 = 'abc0f83a5cadfbc7919d8c6e75731e52f8fe6d8af70f30078ebb3f5e932a00ba'
VERSION = 'music-vertical-transitions-2'
AFFECTED_LANES = ('bass', 'harmony-0', 'harmony-1', 'harmony-2')
MAX_ARRIVALS = 48


@dataclass(frozen=True)
class Slot:
    offset_ticks: int
    root_pc: int
    quality: str
    pitches: tuple[int, int, int, int]


@dataclass(frozen=True)
class Entry:
    key: str
    tier: str
    gesture_id: str
    from_pc: int
    to_pc: int
    signed_semitones: int
    lead_bars: float
    lead_ticks: int
    acknowledgement: str
    slots: tuple[Slot, ...]


def transition_key(tier, from_pc, signed_semitones, lead_bars):
    return f'{tier}:{from_pc}:{signed_semitones}:{lead_bars:g}'


def _candidates(slot, lo, hi):
    upper_lo, upper_hi = max(lo, 52), min(hi, 80)
    if upper_hi - upper_lo < 12:
        upper_lo, upper_hi = lo, hi
    upper = [p for p in range(upper_lo, upper_hi + 1) if p % 12 in slot['pitch_classes']]
    roots = [p for p in range(lo, min(hi, 52) + 1) if p % 12 == slot['root_pc']]
    if not roots:
        roots = [p for p in range(lo, hi + 1) if p % 12 == slot['root_pc']]
    defining = {'dom7': (4, 10), 'dom7b5': (4, 6, 10), 'min7': (3, 10),
                'maj69': (4, 9), 'dim7': (3, 6, 9)}[slot['quality']]
    required = {(slot['root_pc'] + interval) % 12 for interval in defining}
    return [(bass, *notes) for notes in combinations(upper, 3)
            if len({n % 12 for n in notes}) == 3 and notes[-1] - notes[0] <= 16
            and required <= {n % 12 for n in notes}
            for bass in roots if bass < notes[0]]


def _valid_pair(a, b):
    if any(abs(x - y) > 3 for x, y in zip(a[1:], b[1:])):
        return False
    # Bass may leap, but outer voices may not move in parallel perfect fifths.
    return not ((a[3] - a[0]) % 12 == (b[3] - b[0]) % 12 == 7
                and (b[0] - a[0]) * (b[3] - a[3]) > 0)


def voice_entry(row, register_min=28, register_max=96):
    """Bounded dynamic program; call only before playback or for offline audit."""
    options = [_candidates(s, register_min, register_max) for s in row['slots']]
    target = (40, 60, 64, 67)
    paths = {v: (sum(abs(a - b) for a, b in zip(v, target)), (v,)) for v in options[0]}
    for choices in options[1:]:
        next_paths = {}
        for current in choices:
            best = None
            for previous, (cost, path) in paths.items():
                if not _valid_pair(previous, current):
                    continue
                # Prefer held common tones before small moving alternatives.
                move = sum(abs(a - b) for a, b in zip(previous, current))
                held = sum(a == b for a, b in zip(previous[1:], current[1:]))
                candidate = (cost + move - held * 12, path + (current,))
                if best is None or candidate < best:
                    best = candidate
            if best is not None:
                next_paths[current] = best
        paths = next_paths
    if not paths:
        raise ValueError('transition_register_has_no_voice_leading')
    return min(paths.values())[1]


@lru_cache(maxsize=8)
def load_transition_table(register_min=28, register_max=96):
    """Load all 216 entries into an immutable O(1) index; jazz stays disabled."""
    if (type(register_min) is not int or type(register_max) is not int
            or not 0 <= register_min < register_max <= 127):
        raise ValueError('invalid_transition_register')
    data = TABLE_PATH.read_bytes()
    if sha256(data).hexdigest() != TABLE_SHA256:
        raise ValueError('frozen_transition_table_changed')
    table = json.loads(data)
    if table['version'] != '1' or len(table['resolved']) != 216:
        raise ValueError('unsupported_transition_table')
    result = {}
    for row in table['resolved']:
        tier = next((name for name, spec in table['tiers'].items()
                     if row['signed_semitones'] in spec['eligible_signed_semitones']
                     and spec['gesture_by_lead_bars'].get(f"{row['lead_bars']:g}") == row['gesture_id']), None)
        if tier is None:
            raise ValueError('unindexed_transition')
        key = transition_key(tier, row['from_pc'], row['signed_semitones'], row['lead_bars'])
        if key in result or row['to_pc'] != (row['from_pc'] + row['signed_semitones']) % 12:
            raise ValueError('invalid_transition_key')
        voiced = voice_entry(row, register_min, register_max)
        slots = tuple(Slot(s['offset_ticks'], s['root_pc'], s['quality'], v) for s, v in zip(row['slots'], voiced))
        result[key] = Entry(key, tier, row['gesture_id'], row['from_pc'], row['to_pc'],
                            row['signed_semitones'], row['lead_bars'], row['lead_ticks'],
                            table['gestures'][row['gesture_id']]['acknowledgement'], slots)
    return MappingProxyType(result)


def lookup_transition(prepared, from_pc, signed_semitones, lead_bars, *, tier='contract_default'):
    """This edition never enables jazz; a later human decision must amend it."""
    if tier != 'contract_default':
        raise ValueError('jazz_audition_required')
    entry = prepared.get(transition_key(tier, from_pc, signed_semitones, lead_bars))
    if entry is None:
        raise ValueError('transition_not_prepared')
    return entry


def vertical_transition_sidecar(eligible_arrival_ticks):
    """Attach beside canonical schema 0.1 records, never inside those records."""
    ticks = list(eligible_arrival_ticks)
    if not ticks or len(ticks) > MAX_ARRIVALS or any(type(t) is not int or t <= 0 for t in ticks):
        raise ValueError('invalid_transition_arrivals')
    if ticks != sorted(set(ticks)):
        raise ValueError('invalid_transition_arrivals')
    return {'version': VERSION, 'table_id': 'scenescore-transition-table', 'table_version': '1',
            'table_sha256': sha256(TABLE_PATH.read_bytes()).hexdigest(),
            'eligible_arrival_ticks': ticks, 'jazz_enabled': False,
            'audition_status': 'AUDITION_PENDING', 'approval': None}


def select_transition(prepared, arrivals, from_pc, signed_semitones, scene_now, expires_scene,
                      *, seconds_per_tick, bar_ticks=3840, scheduling_margin_s=.175):
    """Bounded selection; callers prepare and validate the arrival list before play.

    The first *feasible* declared arrival wins. Declared lead_bars headroom is
    checked even where the frozen table's actual lead_ticks is shorter. Expiry
    is exclusive, matching Timeline.submit. No past-time slot can be returned.
    """
    if (len(arrivals) > MAX_ARRIVALS or not all(math.isfinite(v) for v in
            (scene_now, expires_scene, seconds_per_tick, scheduling_margin_s))
            or seconds_per_tick <= 0 or scheduling_margin_s < .02):
        raise ValueError('invalid_transition_selection')
    for tick in arrivals:
        arrival = tick * seconds_per_tick
        if arrival >= expires_scene:
            break
        available = arrival - scene_now - scheduling_margin_s
        for lead in (2, 1, .5):
            if lead * bar_ticks * seconds_per_tick > available + 1e-9:
                continue
            entry = lookup_transition(prepared, from_pc, signed_semitones, lead)
            if arrival - entry.lead_ticks * seconds_per_tick >= scene_now + scheduling_margin_s - 1e-9:
                return entry, tick
    raise ValueError('no_feasible_boundary_before_expiry')
