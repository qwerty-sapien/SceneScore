"""Actual frozen-entry voice paths and bounded control-selection invariants."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from modules.music.transitions import (
    TABLE_PATH, TABLE_SHA256, load_transition_table, lookup_transition,
    select_transition, vertical_transition_sidecar,
)


def test_exact_frozen_table_and_all_216_actual_voice_paths():
    assert sha256(TABLE_PATH.read_bytes()).hexdigest() == TABLE_SHA256
    raw = json.loads(TABLE_PATH.read_text())
    prepared = load_transition_table()
    assert len(prepared) == len(raw['resolved']) == 216
    assert sum(e.tier == 'contract_default' for e in prepared.values()) == 72
    assert sum(e.tier == 'auditioned_jazz' for e in prepared.values()) == 144
    for entry in prepared.values():
        assert entry.to_pc == (entry.from_pc + entry.signed_semitones) % 12
        assert entry.slots[-1].offset_ticks == 0
        assert entry.slots[-1].root_pc == entry.to_pc
        assert len(entry.slots) * 4 + 2 <= 24
        row = next(r for r in raw['resolved'] if
                   (r['gesture_id'], r['from_pc'], r['signed_semitones'], r['lead_bars']) ==
                   (entry.gesture_id, entry.from_pc, entry.signed_semitones, entry.lead_bars))
        for slot, source in zip(entry.slots, row['slots']):
            assert all(28 <= p <= 96 for p in slot.pitches)
            assert slot.pitches[0] % 12 == source['root_pc']
            assert {p % 12 for p in slot.pitches[1:]} <= set(source['pitch_classes'])
            assert len({p % 12 for p in slot.pitches[1:]}) == 3
            defining = {'dom7': (4, 10), 'dom7b5': (4, 6, 10), 'min7': (3, 10),
                        'maj69': (4, 9), 'dim7': (3, 6, 9)}[source['quality']]
            assert {(source['root_pc'] + n) % 12 for n in defining} <= {p % 12 for p in slot.pitches}
            assert slot.quality == source['quality']
        for a, b in zip(entry.slots, entry.slots[1:]):
            assert all(abs(x - y) <= 3 for x, y in zip(a.pitches[1:], b.pitches[1:]))
            assert not ((a.pitches[3] - a.pitches[0]) % 12 ==
                        (b.pitches[3] - b.pitches[0]) % 12 == 7 and
                        (b.pitches[0] - a.pitches[0]) * (b.pitches[3] - a.pitches[3]) > 0)
            common = set(p % 12 for p in a.pitches[1:]) & set(p % 12 for p in b.pitches[1:])
            if common:
                assert any(x == y for x, y in zip(a.pitches[1:], b.pitches[1:]))


def test_lookup_returns_cached_identity_and_jazz_stays_unreachable(monkeypatch):
    prepared = load_transition_table()
    assert prepared is load_transition_table()
    monkeypatch.setenv('SCENESCORE_JAZZ_TRANSITIONS', '1')
    for pc in range(12):
        for sign in (-2, 2):
            for lead in (.5, 1, 2):
                entry = lookup_transition(prepared, pc, sign, lead)
                assert entry is prepared[entry.key]
                assert entry.signed_semitones == sign
                with pytest.raises(ValueError, match='jazz_audition_required'):
                    lookup_transition(prepared, pc, sign, lead, tier='auditioned_jazz')
        with pytest.raises(ValueError, match='transition_not_prepared'):
            lookup_transition(prepared, pc, 5, .5)
    with pytest.raises(TypeError):
        prepared['invalid'] = None


@pytest.mark.parametrize('now,lead', [(6.0, .5), (4.0, 1), (2.0, 2)])
def test_declared_lead_must_fit_real_headroom(now, lead):
    # A sparse eligible-boundary fixture exercises all three authored gestures.
    entry, tick = select_transition(load_transition_table(), [11520], 0, 2, now, 9,
                                    seconds_per_tick=60 / 96 / 960)
    assert tick == 11520
    assert entry.lead_bars == lead
    assert tick * 60 / 96 / 960 - entry.lead_bars * 2.5 >= now + .175

def test_near_boundary_uses_next_feasible_internal_bar_then_expiry_rejects():
    arrivals = list(range(3840, 46080, 3840))
    table = load_transition_table()
    entry, tick = select_transition(table, arrivals, 0, 2, 2.45, 8.45,
                                    seconds_per_tick=60 / 96 / 960)
    assert tick == 7680
    assert tick * 60 / 96 / 960 - entry.lead_ticks * 60 / 96 / 960 >= 2.45 + .175
    with pytest.raises(ValueError, match='no_feasible_boundary_before_expiry'):
        select_transition(table, arrivals, 0, 2, 2.45, 5.0, seconds_per_tick=60 / 96 / 960)
    with pytest.raises(ValueError, match='no_feasible_boundary_before_expiry'):
        select_transition(table, arrivals, 0, 2, 27.0, 40.0, seconds_per_tick=60 / 96 / 960)


def test_two_modulations_and_near_miss_hold_return_stable_state():
    # A near-miss harmonic hold supplies no second target: the fixed table resolves
    # its first slot to the single signed destination. Queue ownership is transport.
    table = load_transition_table()
    first = lookup_transition(table, 0, 2, .5)
    second = lookup_transition(table, first.to_pc, -2, .5)
    assert first.slots[-1].root_pc == 2
    assert second.slots[-1].root_pc == 0
    assert second.to_pc == 0


def test_versioned_sidecar_is_unauditioned_and_terminal_excluded():
    source = vertical_transition_sidecar(range(3840, 46080, 3840))
    assert len(source['eligible_arrival_ticks']) == 11
    assert source['eligible_arrival_ticks'][-1] == 42240
    assert source['table_sha256'] == TABLE_SHA256
    assert source['approval'] is None
    assert source['jazz_enabled'] is False
    assert source['audition_status'] == 'AUDITION_PENDING'
    for ticks in ([], [True], [3840, 3840], [7680, 3840], list(range(1, 50))):
        with pytest.raises(ValueError):
            vertical_transition_sidecar(ticks)


def test_loader_rejects_changed_table_before_solving(tmp_path, monkeypatch):
    changed = tmp_path / 'table.json'
    changed.write_text(TABLE_PATH.read_text().replace('"gain_db_delta": 0', '"gain_db_delta": 3'))
    import modules.music.transitions as transitions
    transitions.load_transition_table.cache_clear()
    monkeypatch.setattr(transitions, 'TABLE_PATH', Path(changed))
    with pytest.raises(ValueError, match='frozen_transition_table_changed'):
        transitions.load_transition_table()
    transitions.load_transition_table.cache_clear()


def test_invalid_register_and_insufficient_voice_space_fail_before_play():
    with pytest.raises(ValueError, match='invalid_transition_register'):
        load_transition_table(True, 96)
    with pytest.raises(ValueError, match='transition_register_has_no_voice_leading'):
        load_transition_table(60, 63)
