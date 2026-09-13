# Blink training workspace

Open **Launch Blink Trainer.command** in the repository, or run `make muse-train`.
It builds the page and opens the local workspace at http://127.0.0.1:8767.
The terminal owns a bounded, visible service. Ctrl-C stops it and its acquisition
thread; it expires after an hour. The hosted page is https://scenescore-muse-vertical.vercel.app/train/. Hosted-to-local
access needs the browser’s Local network access permission. The local launcher
avoids that extra step. No headset connection or recording starts merely
because the page is open.

## Connect and collect

Start the same Muse LSL stream you use with RAGTM. Select that exact source in the
training page, enter the actual headset model, and give live-processing consent.
Before real recording, confirm that the selected source and its displayed channel
names, units and rate match your named headset. This records your metadata
confirmation; it does not certify electrode contact or detector performance.
The supplied RAGTM implementation also reads an existing LSL stream. This page
does not assume a remembered headset generation or create a Bluetooth connection
behind the user's back. If the source is unavailable, its blocker stays visible.

The official [MuseLSL guide](https://github.com/alexandrebarachant/muse-lsl/blob/master/README.md)
documents listing headsets and starting an exact named stream with
`muselsl stream --name YOUR_DEVICE_NAME`. MuseLSL itself is not installed by this
task. The page's isolated LSL receiver dependency is prepared separately under
ignored `artifacts/muse-training-runtime`; SceneScore's frozen environment and
dependency locks are unchanged.

Choose a pseudonymous participant ID, refit ID and whole-session role before
recording. Give local-recording consent and press Start recording. The untouched
raw EEG, timestamps, units and gaps are stored beneath ignored
`private_data/02A/training-web`. No EEG is sent to Vercel or GPT.

Use the current trial class and hold **B** over the intended trial, releasing it
afterwards. The default is a comfortable double blink. Record single blinks,
triples, ordinary activity, movement and keypress-only examples too. Guided cues provide
an option without a simultaneous keypress. Keep blinking comfortable and stop
whenever needed. No camera recording is implemented.

## Review and train

Stop recording, select each marked interval, inspect the EEG and adjust the actual
interval/class before confirming it. Keep missed or unclear trials uncertain.
A B interval or cue is an intent marker, not proof of an actual double blink;
the model never receives B/cue timing as an input feature. Labels remain distinct
from detector predictions. [LSL's synchronization documentation](https://labstreaminglayer.readthedocs.io/info/time_synchronization.html)
explains why timestamps from different clocks require an explicit mapping; this
page records keyboard, host receipt and source anchors separately.

Train model fits a small local experimental classifier from reviewed training
windows, with at least three positive and three negative examples. That minimum
only enables the software experiment. It provides no accuracy guarantee. The
model uses a causal two-second EEG window; no future samples or final-test data
enter fitting. Collect whole development sessions after a fresh headset refit to
obtain separate window-level results. Those results are not full-stream event
recall, false activations per hour or a music-control certification.

The default command remains a double blink because it is an explicit sequence
that can be counted while ordinary singles do nothing. This does not establish
that doubles are easier or more separable for this participant. Natural and
intentional blink patterns can overlap, so they need comparison using real data;
[this exploratory study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10213007/)
also distinguishes the question of intention from merely detecting eyelid motion.

The personal window model can be inspected and downloaded locally. Its predictions
are experimental; it cannot automatically arm music or replace the existing
double-only causal detector. A real music-control artifact still needs the held-out
evaluation gates. Synthetic rehearsal is visibly separate and cannot qualify as
real headset training or be mixed into a real model.

## Privacy and lifecycle

Downloads are explicitly requested local exports. Session deletion requires the
exact session ID and invalidates a dependent model. Separately downloaded copies
remain under the user's control and must be removed separately when desired.
No import-time jobs, automatic uploads, remote raw-data storage or global settings
changes are used. A source fault closes the current recording; reconnect starts
a new session rather than hiding a dropout in existing data.

Developer build: `node_modules/.bin/vite build apps/training --base ./ --outDir ../../artifacts/training-dist`.
The webpage is a separate app and does not rebuild the concurrently evolving
music/Blender demonstration.

## Automatic connection diagnostics

After local authentication, the page checks Bluetooth/Muse-service and LSL
metadata every ten seconds, and sample health every second. **Check now** forces
a refresh; **Automatic checks** pauses hardware discovery. No check pairs the
headset, connects an EEG inlet or starts a recording. Use the separate source
connection and recording controls for those actions.

The checklist separates local service, Bluetooth power/permission, a Muse-service
advertisement or macOS connection, an LSL EEG outlet and valid descriptor, the
selected inlet, arriving samples, and signal continuity. Each failure includes a
next action. Timestamped changes appear in connection history. Diagnostic reports
can be downloaded locally; they contain metadata and summary values, no raw EEG
samples or tokens. A changing signal alone does not verify electrode contact.

The local launcher builds a small macOS CoreBluetooth metadata helper. If macOS
permission has not been requested, click **Enable Bluetooth check**, then respond
to the OS prompt. If permission was denied, enable Bluetooth for the app running
the launcher (usually Terminal) in System Settings → Privacy & Security → Bluetooth.
An LSL stream can still work when independent Bluetooth inspection is unavailable.
No visible Muse advertisement is not proof of disconnection; the headset may
already be in use, not advertising, or outside this bounded service scan.

`MUSE_TRANSPORT`, `MUSE_BOARD_ID`, and `MUSE_UNITS` in `.env` are unused placeholders
in this trainer. Leave them blank: transport is LSL, no BrainFlow board ID is used,
and channel units come from the source descriptor (frontal channels require µV).
A BrainFlow board ID selects its hardware driver, not a particular headset's
Bluetooth address: see the [BrainFlow API](https://brainflow.readthedocs.io/en/stable/UserAPI.html).
The distinction between LSL outlets and actual sample receipt is described by the
[LSL user guide](https://labstreaminglayer.readthedocs.io/info/user_guide.html).
Muse-service discovery uses the FE8D service identified by
[MuseLSL](https://github.com/alexandrebarachant/muse-lsl/blob/master/muselsl/constants.py).
