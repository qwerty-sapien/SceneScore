# MU-02 console prototype — 2026-09-13

Direct user authorization: verify charging guidance and make double-blink code.
This is a scoped console prototype, not a new phase or release acceptance.

User-supplied SKU MU-02-BK-EN maps to Muse 2016; BrainFlow MUSE_2016_BOARD is
selected explicitly. Manufacturer MU-02 booklet page 2 prohibits use while
charging (https://fccid.io/2ABZI-MU02/User-Manual/Users-Manual-R1-2835561.pdf).
The user was informed before implementation. Bluetooth was not started while
the user reported charging. Hardware remains unverified.

Added tools/muse_blinks.py, optional dependency requirements, Windows quickstart,
and tools/tests/test_muse_blinks.py. This new heuristic is separate from the
preserved baseline and outputs labelled prototype events, not canonical controls.
No raw recording, cloud upload, audio, approval or production host substitute.

Executed `python -m unittest discover -s tools/tests -p test_muse_blinks.py`:
9 tests passed after fixing waveform rebound de-duplication exposed by a triple
signal test. Coverage includes noise, double/triple signals, sequence closure,
cooldown, flat calibration, invalid timestamps and mocked transport cleanup.
`python tools/muse_blinks.py --simulate --seconds 15`: two candidate blinks and
one synthetic double_blink decision at 11.96875 s. This is software evidence only.
`git diff --check` passed. Full application checks were not run for the isolated
console addition. No real calibration, real accuracy or studio dispatch tested.

No persistent server, capture, agent or container started. Local optional Python
environment is .venv-muse and is ignored. See tools/MUSE_BLINKS.md for exact launch.
Environment creation exited 0. Optional pip install session 88006 exited 1 after
a download timeout/temporary-file WinError 32; BrainFlow is NOT installed. No
installer remains running. The quickstart provides a longer-timeout retry.

## Local HTML test panel continuation

User authorized an HTML app for clean testing. Added tools/muse_test_app.py,
tools/muse-test-ui/{index.html,style.css,app.js}, start-blink-lab.cmd and scoped
HTTP tests. The existing detector's live function now accepts optional event,
sample and cancellation callbacks; console behavior is preserved.

The responsive UI shows calibration, filtered traces, counts and event history.
Synthetic injection passes generated raw waveforms through the Python detector.
The live path requires the user to confirm unplugging, uses the local optional
BrainFlow install and streams only to the loopback page. No EEG persists to disk.
Server binding, Host and mutation Origin checks restrict access; browser loss
stops acquisition after five seconds; sessions have a ten-minute budget.

Validation: 12 scoped unittest tests passed, including actual HTTP simulation
start/calibrate/inject/double detection/stop, origin rejection and static-file
allowlisting. Node syntax check, Python compilation and git diff check passed.
Preview HTTP 200 on 127.0.0.1:8780. CUA returned 'No browser is available', so
browser rendering/interactions and responsive appearance were NOT visually
verified. Real headset testing and optional BrainFlow installation remain open.

Temporary preview was session 32018, Python PID 17384; stopped with Ctrl-C.
No cloud deployment: this is a local hardware testing extension, retaining the
project's local EEG requirement and independent prototype event boundary.
