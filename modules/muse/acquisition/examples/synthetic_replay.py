"""Emit reproducible synthetic replay evidence; temporary raw fixture is removed."""
from pathlib import Path
import tempfile

from modules.muse.acquisition.store import Recorder, encoded
from modules.muse.acquisition.tests.helpers import chunk, metadata
from modules.muse.baseline.replay import replay_session


def main():
    with tempfile.TemporaryDirectory(prefix="scenescore-synthetic-replay-") as temporary:
        path = Path(temporary) / "session"
        recorder = Recorder(path, metadata(), explicitly_started=True)
        recorder.append(chunk(count=257))
        values = [0.0] * 700
        for center in (75, 160):
            for j in range(center - 12, center + 13):
                values[j] = 200 * (1 - abs(j - center) / 13)
        for sequence, offset in enumerate(range(0, len(values), 64), start=1):
            rows = values[offset:offset + 64]
            value = chunk(sequence, 257 + offset, len(rows))
            value["samples"] = [[v, v] for v in rows]
            recorder.append(value)
        recorder.close()
        first = replay_session(path, arm_after_s=1.0)
        second = replay_session(path, arm_after_s=1.0)
        assert first == second
        accepted = [e for e in first["events"] if e["kind"] == "GestureEvent" and e["status"] == "accepted"]
        assert len(accepted) == 1
        first.update(deterministic_second_replay_equal=True, accepted_synthetic_doubles=len(accepted),
                     evidence_scope="Software fixture only; no real blink accuracy, clock, or hardware claim")
        print(encoded(first).decode(), end="")


if __name__ == "__main__":
    main()
