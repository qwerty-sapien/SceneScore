import copy
import math
import time

import pytest

from services.bridge.server import Companion, chunk, synthetic_metadata
from modules.muse.training.checkpoints import CheckpointStore, fit_checkpoint, _digest
from modules.muse.training.tests.test_checkpoints import checkpoint, contract, examples


def companion(tmp_path):
    meta = synthetic_metadata()
    meta["sample_rate_hz"] = 64
    result = Companion(meta, checkpoint_root=tmp_path)
    result.connected, result.quality = True, "good"
    result.detector.count = 128
    return result


def feed(companion, start=0, seconds=2):
    for i in range(int(seconds * 64) // 32):
        times = [start + (i * 32 + j) / 64 for j in range(32)]
        rows = [[math.sin(t * 8), math.cos(t * 11)] for t in times]
        companion.last_subscriber_s = time.monotonic()
        previous = companion.detector.previous
        sequence = previous['sequence'] + 1 if previous else 0
        index = previous['sample_start_index'] + len(previous['samples']) if previous else 0
        companion.consume(chunk(companion.metadata, rows, times, sequence, index, time.monotonic(), companion.host_epoch))


def test_latest_below_target_loads_next_arm_and_is_pinned(tmp_path):
    store = CheckpointStore(tmp_path)
    first = store.save(checkpoint())
    store.save_evaluation(first["id"], {"precision": .60, "recall": .7, "complete": True, "target_reached": False})
    bridge = companion(tmp_path)
    armed = bridge.arm()
    assert armed["active_checkpoint_id"] == first["id"] and armed["arming"]
    assert not armed["armed"] and armed["evaluation"]["precision"] == .6
    feed(bridge)
    assert bridge.status()["armed"]
    second = store.save(fit_checkpoint(examples(50), contract(), first))
    assert bridge.arm()["active_checkpoint_id"] == first["id"]
    assert bridge.detector.checkpoint["model"]["weights"] == first["model"]["weights"]
    with pytest.raises(ValueError, match="disarm"):
        bridge.select_checkpoint(second["id"])
    bridge.disarm()
    feed(bridge, 2)
    assert bridge.arm()["active_checkpoint_id"] == second["id"]
    assert bridge.status()["evaluation"] is None
    feed(bridge, 4)
    assert bridge.status()["armed"]
    assert bridge.clock()["config_hash"] != first["model"]["config_sha256"]
    store.save_evaluation(second["id"], {"precision": .8, "recall": .85, "complete": False})
    assert bridge.status()["evaluation"] is None  # Existing arm retains its snapshot.
    bridge.disarm()
    feed(bridge, 6)
    assert bridge.arm()["evaluation"]["precision"] == .8


def test_rollback_compatibility_and_corruption_do_not_depend_on_accuracy(tmp_path):
    store = CheckpointStore(tmp_path)
    first = store.save(checkpoint())
    store.save(fit_checkpoint(examples(50), contract(), first))
    bridge = companion(tmp_path)
    bridge.select_checkpoint(first["id"])
    assert bridge.arm()["active_checkpoint_id"] == first["id"]
    bridge.disarm()
    feed(bridge)
    bridge.select_checkpoint("baseline")
    assert bridge.arm()["active_checkpoint_id"] is None
    bridge.disarm()
    wrong = store.save(checkpoint(rate=128))
    with pytest.raises(ValueError, match="contract"):
        bridge.select_checkpoint(wrong["id"])
    (tmp_path / "checkpoints" / (first["id"] + ".json")).write_text("{}")
    with pytest.raises(ValueError):
        bridge.select_checkpoint(first["id"])
    assert first["id"] in bridge.checkpoint_catalog()["invalid_checkpoint_ids"]


def test_quality_loss_cancels_pending_arm_and_does_not_replace_saved_weights(tmp_path):
    store = CheckpointStore(tmp_path)
    first = store.save(checkpoint())
    bridge = companion(tmp_path)
    bridge.arm()
    raw = chunk(bridge.metadata, [[1, 2]], [0], 0, 0, time.monotonic(), bridge.host_epoch, quality="bad")
    bridge.consume(raw)
    assert not bridge.pending_arm and not bridge.detector.armed
    assert store.load(first["id"])["model"] == first["model"]


@pytest.mark.parametrize("bias", [-40., 40.])
def test_classifier_rejects_events_without_bypassing_closed_double_grammar(tmp_path, bias):
    from modules.muse.training.personal_detector import PersonalDetector
    model = checkpoint()
    reject = copy.deepcopy(model)
    reject["model"]["weights"] = [0.] * 14
    reject["model"]["bias"] = bias
    reject["id"] = "checkpoint-" + _digest({k: v for k, v in reject.items() if k != "id"})
    bridge = companion(tmp_path)
    detector = PersonalDetector(bridge.metadata, reject)
    detector.count = 64
    detector.arm()
    emitted = []
    for i in range(28):
        times = [(i * 32 + j) / 64 for j in range(32)]
        def row(t):
            pulse = sum(180 * max(0, 1 - abs(t - p) / .09) for p in [3., 3.3, 7., 9., 9.3, 9.6])
            return [pulse + math.sin(t * 12), .94 * pulse + math.cos(t * 13)]
        _, gestures = detector.consume(chunk(bridge.metadata, [row(t) for t in times], times, i, i * 32,
                                             time.monotonic(), bridge.host_epoch))
        emitted.extend(gestures)
    accepted = [g for g in emitted if g["status"] == "accepted"]
    if bias < 0:
        assert emitted and not accepted
        assert any(g["reason"] == "personal_model_rejected" for g in emitted)
    else:
        assert len(accepted) == 1 and accepted[0]["gesture_count"] == 2
    assert any(g["gesture_count"] in (1, 3) for g in emitted)
