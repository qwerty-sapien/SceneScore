# BrainFlow connection follow-up — 2026-09-13

The user's standalone BrainFlow log discovered Muse-AD3C. It did not include
`CONNECTED` or a received data shape, so discovery is the only observed hardware
result. No competing live connection was initiated during this change.

Direct trainer Bluetooth now uses `MUSE_2_BOARD` (38), a 15-second discovery
timeout and the installed BrainFlow 5.22.2 runtime. A child process runs native
calls on its main thread; the parent bounds setup/read waits, supports Cancel,
retains the exact child handle and reaps it on close. Its bounded ring buffer is
read in batches of at most 128. EEG rows and original timestamp values pass
through unchanged, with backlog/stale-clock rejection. Original board metadata
is retained with hardware verification false and device identity unknown.

Connect still precedes the in-memory EEG check, and Train receives that same
source. Existing LSL and explicit synthetic paths remain available. No fitting,
checkpoint, evaluation, frozen contract or studio BLE behavior was changed.
The optional runtime requirements now include BrainFlow 5.22.2.

Commands actually run:

- `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests/test_brainflow_source.py services/training/tests/test_preparation.py`
  — passed, 18 tests in 6.29 seconds. Fixtures verify the board setup, four EEG
  rows, unchanged timestamps, empty pulls, stale/backlogged data, partial-open
  cleanup, failed-stop cleanup, helper protocol, cancellation, process exit,
  default backend selection and the existing preflight/handoff behavior.
- `.venv/bin/python -m ruff check services/training/brainflow_source.py services/training/preparation.py services/training/tests/test_brainflow_source.py`
  — passed.
- Scoped `git diff --check` — passed.
- Read-only BrainFlow getters using the launcher's exact PYTHONPATH — passed:
  version 5.22.2, board 38, TP9/AF7/AF8/TP10, 256 Hz. No prepare/start call.

No browser rebuild was needed because this change only replaces the backend
connection adapter. No broad regression, real collection, real training or
headset accuracy measurement was run. Test-owned helper processes were explicitly
reaped and their exit state asserted; the test command exited successfully.
The user-owned launcher/script was not stopped by this task. Restart the old launcher after
the standalone script releases the Muse, then connect using `make muse-train`.

Reference: [BrainFlow's Muse 2 setup](https://brainflow.readthedocs.io/en/stable/SupportedBoards.html#muse-2).
