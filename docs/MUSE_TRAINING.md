# Personal blink trainer

Open **Launch Blink Trainer.command** in SceneScore, or run `make muse-train`.
The launcher builds and opens an authenticated page at `http://127.0.0.1:8767`.
Everything runs locally; no Vercel page, account or internet connection is needed.
There is no token field: use the page opened by the launcher.

1. **Connect headset.** Switch on your Muse and close other apps using it. The
   trainer uses direct Bluetooth with a 15-second discovery window, or reuses a
   single compatible LSL stream if one is already running. Keep only the intended
   Muse powered on. Finish standalone headset test scripts first.
2. **Check EEG.** Keep the headset in place. The page checks at least three seconds
   of fresh, continuous EEG with measurable variation on both frontal channels.
   Flat, missing, stale or inconsistent samples keep Train unavailable. This check
   keeps samples in memory and does not record or fit a model.
3. **Train.** Once EEG is detected, click Train. Blink twice, then press **B** once
   within one second **after the second blink**, for every deliberate double blink.

The B indicator briefly lights
only after the label is stored. Held keys do not create repeated labels. Mark
all deliberate doubles: unmarked, sufficiently distant windows are assumed to
be background. Training, raw EEG, labels and saved models stay on your machine.
No EEG is uploaded anywhere.

The trainer discovers the single compatible source automatically. It requires
AF7/AF8 or FP1/FP2 channels with microvolt units and a supported sample rate.
Missing headsets or ambiguous LSL streams produce instructions in the status line.
The Bluetooth path uses the shared classic Muse decoder and Bleak manager in a
bounded local helper. Cancel and shutdown reap that helper even if a native call
hangs. Search, connection and EEG checks report distinct progress. The discovered
name and transport metadata are saved without inferring electrode contact or
hardware verification. Finding a Muse still does not enable Train until EEG is
measurable. An empty scan asks for a power cycle, without assuming the headset
was off.

BrainFlow 5.22.2 remains an explicit developer adapter only. A live stack sample
of the user's standalone test confirmed a native scan-callback deadlock, so the
normal trainer avoids that wrapper. Optional runtime dependencies are listed in
`tools/muse-training-requirements.txt`; the launcher does not install packages.
After updating the backend, stop the old launcher with Ctrl+C and run
`make muse-train` again.
For this connection workaround specifically, an already-running launcher also
uses the direct Bluetooth helper on its next Connect; it need not be restarted.

Click **Stop** at any time. Each click runs for at most ten minutes; leaving the
page stops setup or collection; losing focus stops active training. Native
Bluetooth permission dialogs may take focus during setup. Reconnect
and check EEG again before the next training run. Successful training updates are
saved before evaluation. If there are too few examples to fit a first model,
recordings and labels still remain available for the next run.

The first fit needs 20 usable double-blink windows and 20 background windows.
Each window contains two seconds of EEG features. Background excludes a
two-second margin around B labels. Later updates need at least ten additional
usable examples of each class, start from compatible saved weights, and reuse
the saved feature definitions and scaler. A bounded, deterministic batch mixes
new and historical examples. Keyboard timing is label metadata, never an input
feature. Automatic model-generated labels are not used.

After saving, the complete detector is frozen for a fresh check. Check data is
excluded from fitting, scaler calculation and threshold selection. A complete
check requires 30 B-labelled doubles, 120 monitored seconds and 60 seconds of
background exposure. Matching uses the final detected blink from one second
before to 250 ms after each B source-time anchor, one-to-one. Duplicate and
unmatched detections count as false positives; unmatched labels count as misses,
including misses during signal problems.

**93% is advisory.** Both unrounded precision and recall must exceed 93%, with
at least 95% usable-stream availability, to finish automatically at the target.
Otherwise the trainer gathers more learning examples, updates, and starts a
fresh check. Results describe **agreement with your B labels**, not independently
verified blink accuracy. Incomplete evidence is labelled; no evaluation means
“Not yet evaluated.” No real headset accuracy has been measured by the fixture
tests shipped with this change.

The next **Arm** in the studio loads the latest compatible valid checkpoint,
including one below 93% or without evaluation. A new checkpoint resets warmup
and partial gestures. Its weights stay fixed throughout that armed session.
The existing detector details show the active checkpoint and B-label estimates;
while disarmed, select an older compatible checkpoint or the causal baseline
for rollback. Stream quality, closed-double grammar, single/triple rejection,
and approved musical-plan requirements still apply.

Data is stored under `private_data/02A/training-web/automatic/`: immutable
`checkpoints/`, advisory `evaluations/`, and versioned exploratory `runs/` with
raw samples, labels, learning examples, stage boundaries and detector decisions.
Every checkpoint has a content hash, parent, weights, scaler, configuration,
training-step count and learning-data hash. Interrupted or invalid writes do
not replace older checkpoints. Corrupt or incompatible artifacts cannot load;
low measured agreement never invalidates one. Keep this local folder to resume
training and retain rollback history. Frozen canonical contract 0.1 and its
independently reviewed evaluation datasets are unchanged.

Developer build:

```sh
node_modules/.bin/vite build apps/training --base ./ --outDir ../../artifacts/training-dist --emptyOutDir
```

Explicit synthetic rehearsal is available only through the local service's
`--synthetic-rehearsal` flag. It is visibly marked and cannot silently substitute
for a headset or load as a real-device model. The older reviewed collection and
diagnostics APIs remain developer interfaces; their controls are absent from
the normal training page.
