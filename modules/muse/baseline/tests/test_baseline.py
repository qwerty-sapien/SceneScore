import json
from pathlib import Path
import random
import subprocess
import pytest
from modules.muse.acquisition.tests.helpers import metadata, chunk, ROOT
from modules.muse.baseline.causal import CausalBaseline, Config, Grammar
from modules.muse.baseline.ragtm import RagtmCandidatePort


def candidate(index, onset, end=None):
    value = json.loads((ROOT/'fixtures/contracts/BlinkCandidate.json').read_text())
    value['id'] = f'c-{index}'
    value['start']['seconds'], value['end']['seconds'] = onset, onset+.1 if end is None else end
    return value


def test_port_matches_verbatim_original_candidate_oracle_on_synthetic_filtered_samples():
    rng = random.Random(42)
    rows = []
    for i in range(1500):
        values = {name: rng.gauss(0, 8) for name in ['AF7', 'AF8', 'TP9']}
        if i in [0, 20, 255, 256, 270, 322, 400, 700, 900, 965, 1200]:
            values.update(AF7=220, AF8=-190)
        rows.append({'time': i*1000/256, 'values': values})
    data = {'channels': ['AF7', 'AF8', 'TP9'], 'rate': 256, 'rows': rows}
    result = subprocess.run(['node', str(Path(__file__).with_name('ragtm_oracle.mjs'))],
                            input=json.dumps(data), text=True, capture_output=True, check=True, timeout=10)
    original = json.loads(result.stdout)
    port = RagtmCandidatePort(data['channels'], data['rate'])
    assert [port.feed(x['values'], x['time']) for x in rows] == original
    assert sum(original) > 0


@pytest.mark.parametrize('count,accepted', [(1, False), (2, True), (3, False)])
def test_sequence_closure_prevents_prefix_double(count, accepted):
    grammar = Grammar(metadata())
    for i in range(count):
        assert grammar.feed(candidate(i, 1+i*.3)) == []
        assert grammar.advance(1+i*.3+.3) == []
    result = grammar.advance(3)
    assert len(result) == 1
    assert (result[0]['status'] == 'accepted') == accepted
    assert result[0]['closure_delay_s'] == 3-result[0]['final_blink']['seconds']
    assert grammar.advance(4) == []


def test_duplicate_stale_and_boundary_third():
    grammar = Grammar(metadata())
    first = candidate(0, 1)
    grammar.feed(first)
    assert grammar.feed(first) == []
    grammar.feed(candidate(1, 1.4))
    # Inclusive max gap: a third onset exactly at closure prevents a double.
    assert grammar.feed(candidate(2, 2.0)) == []
    result = grammar.advance(3)
    assert result[0]['status'] == 'rejected'
    with pytest.raises(ValueError):
        grammar.feed(candidate(3, .5))


def test_overlong_train_has_explicit_diagnostic_not_truncated_double():
    grammar = Grammar(metadata())
    for i in range(30):
        assert grammar.feed(candidate(i, 1+i*.3)) == []
    assert len(grammar.pending) <= 4
    assert grammar.advance(20) == []
    assert grammar.last_rejection['reason'] == 'overlong_train'


def test_close_spaced_ambiguous_and_cooldown_sequences_rejected():
    grammar = Grammar(metadata())
    grammar.feed(candidate(0, 1))
    grammar.feed(candidate(1, 1.12))
    assert grammar.advance(2)[0]['status'] == 'rejected'
    grammar.feed(candidate(2, 3))
    grammar.feed(candidate(3, 3.3))
    assert grammar.advance(4)[0]['status'] == 'accepted'
    grammar.feed(candidate(4, 4.1))
    grammar.feed(candidate(5, 4.4))
    assert grammar.advance(5.01)[0]['status'] == 'rejected'


def test_reset_clears_partial_sequence():
    grammar = Grammar(metadata())
    grammar.feed(candidate(0, 1))
    grammar.reset()
    grammar.feed(candidate(1, 1.4))
    assert grammar.advance(3)[0]['gesture_count'] == 1


def test_warmup_quality_gap_and_explicit_rearm():
    detector = CausalBaseline(metadata())
    with pytest.raises(ValueError):
        detector.arm()
    detector.consume(chunk(count=256))
    detector.arm()
    detector.consume(chunk(1, 256, quality='bad'))
    assert not detector.armed
    with pytest.raises(ValueError):
        detector.arm()
    detector.consume(chunk(2, 320, count=256))
    assert not detector.armed
    detector.arm()
    detector.consume(chunk(3, 580, gap=4))
    assert not detector.armed
    assert detector.reason == 'gap_or_reconnect_rearm_required'


def test_stale_chunk_fault_disarms_before_error():
    detector = CausalBaseline(metadata())
    detector.consume(chunk(count=256))
    detector.arm()
    with pytest.raises(ValueError):
        detector.consume(chunk(count=256))
    assert not detector.armed


def run_waveform(batch):
    detector = CausalBaseline(metadata())
    detector.consume(chunk(count=256))
    detector.arm()
    values = [0.0] * 700
    for center in [75, 160]:
        for j in range(center-12, center+13):
            values[j] = 200*(1-abs(j-center)/13)
    candidates, gestures = [], []
    seq = 1
    for offset in range(0, len(values), batch):
        selection = values[offset:offset+batch]
        data = chunk(seq, 256+offset, len(selection))
        data['samples'] = [[v, v] for v in selection]
        a, b = detector.consume(data)
        candidates += a
        gestures += b
        seq += 1
    return candidates, gestures


def test_causal_waveform_hysteresis_and_chunk_partition_invariance():
    a, b = run_waveform(1)
    c, d = run_waveform(73)
    assert a == c and b == d
    assert len(a) == 2
    assert len(b) == 1 and b[0]['status'] == 'accepted'
    assert all(x['score_type'] == 'uncalibrated' for x in a)


@pytest.mark.parametrize('changes', [{'high_z': 1}, {'floor_uv': 0}, {'max_gap_s': -.5}, {'lowpass_hz': float('nan')}])
def test_invalid_exploratory_parameters_rejected(changes):
    with pytest.raises(ValueError):
        Config(**changes)


def test_no_guessed_channels_or_units():
    meta = metadata()
    meta['channels'][0]['name'], meta['channels'][1]['name'] = 'TP9', 'TP10'
    with pytest.raises(ValueError):
        CausalBaseline(meta)


def test_malformed_chunk_resets_armed_detector():
    detector = CausalBaseline(metadata())
    detector.consume(chunk(count=256))
    detector.arm()
    malformed = chunk(1, 256)
    malformed['samples'][0][0] = float('nan')
    with pytest.raises(ValueError):
        detector.consume(malformed)
    assert not detector.armed


def test_host_epoch_reset_requires_rearm():
    detector = CausalBaseline(metadata())
    detector.consume(chunk(count=256))
    detector.arm()
    next_chunk = chunk(1, 256)
    next_chunk['host_receipt']['epoch'] = 'new-host'
    detector.consume(next_chunk)
    assert not detector.armed


def test_grammar_rejects_time_reversal_after_decision():
    grammar = Grammar(metadata())
    grammar.feed(candidate(0, 1))
    grammar.advance(2)
    with pytest.raises(ValueError):
        grammar.feed(candidate(1, 1.7))


def test_bad_quality_candidate_never_gets_good_quality_gesture():
    grammar = Grammar(metadata())
    first = candidate(0, 1)
    first['quality'] = {'state': 'unverified', 'reason': 'unmeasured'}
    grammar.feed(first)
    grammar.feed(candidate(1, 1.4))
    result = grammar.advance(3)[0]
    assert result['status'] == 'rejected'
    assert result['quality']['state'] == 'unverified'
