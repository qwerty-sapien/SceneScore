# MU-02 double-blink prototype

## Browser test panel

Double-click `start-blink-lab.cmd` in the SceneScore folder, or run:

```powershell
.\.venv-muse\Scripts\python.exe tools/muse_test_app.py
```

Open http://127.0.0.1:8780. Start simulation, wait three seconds for calibration,
then use Single, Double or Triple to inject actual generated waveforms through
the Python detector. Counters, filtered AF7/AF8 traces and event history update
live. Simulation requires only Python's standard library.

For real hardware choose Muse MU-02, confirm the headset is unplugged, and connect.
BrainFlow must be installed in the interpreter running the server (see below).
Real calibration takes ten seconds. Change threshold between sessions; restart
to recalibrate. Stop releases Bluetooth. Sessions stop after ten minutes, or
after five seconds without browser polling. Ctrl-C stops the server. Keep the
terminal open while testing. No raw files, cloud calls or music controls are used.

The UI is served from the existing local Python prototype, not the production
studio. Events remain experimental. Run all scoped tests with
`python -m unittest discover -s tools/tests -p "test_muse*.py"`.

The MU-02 manufacturer manual explicitly prohibits use while charging:
https://fccid.io/2ABZI-MU02/User-Manual/Users-Manual-R1-2835561.pdf (page 2).
Charge off-head; unplug, turn on and fit before connecting. Close phone Muse apps.

From SceneScore in PowerShell:

```powershell
python -m venv .venv-muse
.\.venv-muse\Scripts\python.exe -m pip install --timeout 120 -r tools/muse-blinks-requirements.txt
.\.venv-muse\Scripts\python.exe tools/muse_blinks.py
```

No hardware/dependencies needed for the fast software demonstration:

```powershell
python tools/muse_blinks.py --simulate --seconds 15
python -m unittest discover -s tools/tests -p test_muse_blinks.py
```

Real runs last 120 seconds by default; Ctrl-C releases Bluetooth. During the first
10 seconds sit relaxed. After READY, double blink naturally and watch stdout for
`double_blink`. Use `--name Muse-1234` to select your exact Bluetooth name if needed.
`--threshold 4` increases sensitivity; `--threshold 6` reduces it. Refit and restart
to recalibrate. Settings are unvalidated starting points, not universal values.

Setup status on this machine: .venv-muse was created, but the initial BrainFlow
download timed out (9.7/31.2 MB) and pip exited with WinError 32 on its temporary
download. Dependencies are not installed yet. Retry the install command above;
the simulation and unit tests already run with the existing Python interpreter.

This NEW exploratory detector is independent of the preserved RAGTM baseline.
It uses causal 0.5-Hz baseline removal, 10-Hz smoothing, per-channel robust noise
calibration, bilateral AF7/AF8 excursions, hysteresis and 40–450-ms waveform bounds.
An excursion has a 150-ms refractory period after return to baseline; accepted
peaks must be at least 200 ms apart. A train closes 500 ms after its last waveform
ends; exactly two qualify, with a one-second cooldown. A third blink suppresses
the entire train. Closing after the second is essential to avoid triggering on a
triple prefix. Timing differs from a peak-to-peak 700-ms rule.

Events are prototype JSONL, not canonical SceneScore GestureEvent/ControlAction
records. They do not start music or approve a plan. All processing stays local;
no raw EEG files are written, no upload/server starts. BrainFlow board metadata
selects channels and rate; timestamps are BrainFlow transport timestamps, not a
verified hardware-to-audio clock mapping. Invalid/gapped timestamps stop the run
and require restart. Flat calibration is rejected. Contact quality, motion and
natural-double-blink intent remain unverified; no clinical or accuracy claims.
This console prototype needs real wearer testing before studio integration.

Try isolated singles, doubles, triples, talking and head movement. Record false
triggers and missed doubles independently. The synthetic demonstration and unit
tests verify software only; they cannot establish real Muse performance.
