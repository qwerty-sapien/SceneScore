import pytest
from modules.muse.acquisition.store import Recorder
from modules.muse.acquisition.tests.helpers import metadata, chunk
from modules.muse.annotation.workflow import cues, confirm, label


@pytest.fixture
def session(tmp_path):
    recorder = Recorder(tmp_path/'s', metadata(), explicitly_started=True)
    recorder.append(chunk())
    recorder.close()
    return recorder.path


def label_args():
    return dict(reviewer='reviewer-01', source='independent_observation', evidence_ref='local-note-01',
                epoch='fixture-1', onset_s=.01, end_s=.2, final_blink_s=.15, gesture_count=2,
                intent='deliberate', certainty='verified')


def test_cues_and_delayed_responses_never_truth(session):
    schedule = cues(session, mode='randomized_instructed', seed=5, count=4)
    assert all(not x['is_ground_truth'] for x in schedule)
    assert len({round(b['scheduled_protocol_s']-a['scheduled_protocol_s'], 5)
                for a, b in zip(schedule, schedule[1:])}) == 3
    response = confirm(session, schedule[0]['id'], performed='performed', confirmation_s=30)
    assert not response['is_ground_truth']
    assert not (session/'labels.jsonl').exists()


def test_review_relabel_appends_and_preserves_history(session):
    original = label(session, **label_args())
    updated = label_args() | {'certainty': 'uncertain', 'supersedes': original['id']}
    result = label(session, **updated)
    assert not result['is_ground_truth']
    assert len((session/'labels.jsonl').read_text().splitlines()) == 2


@pytest.mark.parametrize('source', ['detector', 'cue', 'prediction', 'keyboard_during_blink'])
def test_predictions_and_prompt_times_cannot_become_truth(session, source):
    with pytest.raises(ValueError):
        label(session, **(label_args() | {'source': source}))


def test_label_needs_evidence_and_valid_timing(session):
    with pytest.raises(ValueError):
        label(session, **(label_args() | {'end_s': 0}))
    with pytest.raises(ValueError):
        label(session, **(label_args() | {'evidence_ref': ''}))
    with pytest.raises(ValueError):
        confirm(session, 'missing', performed='performed', confirmation_s=20)


def test_unknown_epoch_and_synthetic_truth_guard(session):
    with pytest.raises(ValueError, match='outside_recorded_epoch'):
        label(session, **(label_args() | {'epoch': 'not-recorded'}))
    annotation = label(session, **label_args())
    assert annotation['source_mode'] == 'synthetic'
    assert annotation['is_ground_truth'] is False
