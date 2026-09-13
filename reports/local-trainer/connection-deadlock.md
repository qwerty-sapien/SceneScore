# Connection failure follow-up — 2026-09-13

Confirmed cause of the BrainFlow hang: the user's standalone Python test
(PID 90889, Terminal parent 83044, launched 14:29:44) remained inside
`prepare_session`. A one-second macOS stack sample showed:

- Main thread: Muse prepare → BLELibBoard callback setter → SimpleBLE callback
  setter → callback mutex wait.
- CoreBluetooth discovery thread: SimpleBLE scan callback → Muse callback →
  BLELibBoard peripheral identifier → wrapper mutex wait.

The [BrainFlow 5.22.2 wrapper source](https://github.com/brainflow-dev/brainflow/blob/5.22.2/src/board_controller/ble_lib_board.cpp)
holds its wrapper mutex while calling SimpleBLE. This matches the observed lock
cycle, before any completed headset connection or EEG stream. The stopped test
was identified by exact PID, start time, terminal input and loaded native
libraries; SIGTERM was sent only to that process and its exit was confirmed.
Other Python jobs and the user's training service (97460) were not stopped.

The trainer now avoids that wrapper by using the existing classic Muse Bleak
adapter in its owned helper. Discovery lasts 15 seconds; setup and reads remain
bounded, cancellation reaps the helper, and search/connection progress is distinct
from EEG checks. The old no-argument helper protocol also chooses this backend
without new progress frames, so an already-running launcher gets the workaround
on its next Connect. BrainFlow remains an explicit `--brainflow` developer option.
No package binary, global configuration, frozen schema, learning behavior or
checkpoint was modified. This supersedes the earlier BrainFlow-default report.

Hardware outcome remains incomplete. The bounded direct scan after stopping the
deadlocked test found no Muse. The helper scan after the user's first power cycle
also found none. After the user confirmed phone/tablet Bluetooth off and another
headset restart, the final helper scan again completed without finding a Muse.
No EEG was received or recorded. The macOS metadata query reported Bluetooth
allowed/on and no connected FE8D peripheral. These results do not establish that
the headset is switched off, faulty, or incapable of advertising to another host.

Verification actually run:

- `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests/test_brainflow_source.py services/training/tests/test_preparation.py`
  — final result: **22 passed in 6.93 seconds**.
- `.venv/bin/python -m ruff check services/training/brainflow_source.py services/training/preparation.py services/training/tests/test_brainflow_source.py`
  — passed.
- Scoped `git diff --check` — passed.
- Bounded diagnostic Python PIDs 2011, 3123 and 5826 each reported their worker
  closed and exited successfully. Helper close waits for exact child termination.
  Test fixtures also assert child exit, including cancellation and legacy IPC.

No frontend change or build was necessary. No additional hardware scans are
running. Physical discovery and headset EEG readiness remain unverified; the
next useful observation is whether the official Muse app can discover/connect
to this powered headset, to distinguish host discovery from headset availability.
