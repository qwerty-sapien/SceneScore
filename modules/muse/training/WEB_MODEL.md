# Personal reviewed blink windows

`train_model(examples)` returns `{model, report}`. `predict_window(model,
times_s, samples, sample_rate_hz)` returns a scalar **uncalibrated window score**.
The model is separate from the causal candidate/closure detector and always
has `control_authority:false`. It cannot dispatch music, arm a headset, certify
signal contact or label training examples. A high score does not establish
deliberate intent. Triple is a negative example class and never enables a triple
control.

The backend assembles each reviewed example using the frozen training API:
`session_id`, `participant_id`, `refit_id`, `role`, `source_mode`, `review_id`,
`certainty`, `class_name`, `times_s`, `samples`, `sample_rate_hz`, `start_s`, and
`end_s`. Source mode is either `synthetic` or `real_device`, and they cannot be
mixed. Class is double, single, triple, natural, artifact or keypress_only.
Only double is positive. At least three positive and three negative reviewed
TRAIN windows are required. Uncertain reviews are excluded with their IDs and a
reason in the report. A final-test entry fails immediately before its waveform
is read. The endpoint is not a final-test evaluator.

The model is personal: one participant, consistent sampling rate, and consistent
whole-session source/refit/role identity. The same participant/refit cannot
appear in both training and development, including in uncertain examples.
Reviewer IDs cannot duplicate. Within each session, reviewed intervals and their
two-second feature windows cannot overlap. Exact copied windows and consecutive
copied waveform runs of at least 100 ms are rejected across reviews/recordings,
even if timestamps or IDs were changed. This catches exact-copy augmentation; it
does not claim to identify all transformed/resampled duplication. Separate
numeric device times are not assumed to share a clock epoch. Backend epoch and
raw provenance checks remain necessary.

For training, the feature window is the two seconds ending at the human-reviewed
`end_s`. For streaming prediction, it ends at the last supplied sample. Extra
preceding data is ignored. Samples after a fixed training endpoint never enter
features or scaling. The window requires nearly two seconds of coverage at the
declared rate, strictly increasing finite source timestamps, bounded sample-gap
and density checks, and exactly two finite nonflat frontal EEG columns. Neither
client time, B-key state, cue time, review class, session ID nor human interval
onset enters the feature vector. Input hashes bind the exact supplied examples,
including metadata, independently of feature selection.

The backend must preserve the same verified frontal channel order and units
across sessions and prediction. The narrow model seam has no channel/unit/epoch
fields and cannot independently establish those acquisition facts. A
`real_device` source label is supplied by the audited backend; the model does not
turn that string into hardware validation or consent evidence.

Fourteen deterministic EEG features describe two-second waveform structure:
number of smoothed excursions, two-peak structure, third-peak presence,
inter-peak gap, second/first peak ratio, peak width, active fraction, bilateral
correlation and amplitude balance, interchannel difference, high-frequency
roughness, slow drift, signal RMS and relative noise floor. Centering and shape
calculations use only the completed past window. There is no invented IMU or
motion sensor; roughness/drift are waveform descriptions. Feature peak regions
are not physiological labels and do not replace the repository closure grammar.

Training uses only TRAIN windows for scaling and a class-balanced L2 logistic
fit, with exactly 200 gradient updates. Config and feature version are frozen and
hashed. Standardized values are bounded to limit numerical outliers. Limits are
256 supplied reviews, one million supplied timestamps in total, at most 16,384
samples per input buffer, and sampling rates 32–2,048 Hz. No optimizer search,
pseudolabels, neural dependency, online adaptation or development tuning occurs.

The returned model includes the UI summary fields (`id`, `status`, class counts,
source mode, held-out result, model kind, and false control authority), coefficients,
feature names, scaler, threshold, exact training-data/config hashes and a compact
example manifest. The ID hashes fitted model content and training lineage;
adding development results does not change fitted identity. Source strings and
hashes are provenance, not attestations. Real fits are `REAL_DATA_EXPLORATORY`;
synthetic fits are `PIPELINE_TESTED_ONLY`.

Whole development sessions are optional and never affect fitting or scaling.
Their report explicitly counts windows and positive/negative denominators, with
TP/TN/FP/FN, window recall, precision and specificity at the fixed 0.5 threshold.
Zero denominators stay null. With no reviewed development windows, the result
is null with a reason. No training accuracy is reported, and no window metric is
called event recall, false activations per hour, intent accuracy or music latency.
Missing negative classes remain visible in `negative_class_counts`, including
keypress-only comparisons needed to assess motor/timing confounding.

Validation uses visibly synthetic noisy two-frontal fixtures, including separate
double, single, triple, natural, artifact and keypress-like shapes. Passing those
fixtures demonstrates model plumbing and separability of the fixture shapes,
not performance on a person's EEG. Focused tests also exercise train-only
scaling, strict source/split/refit gates, duplicate/overlap rejection, uncertainty,
future-data exclusion, invalid windows, determinism and no-data failure.

Actual command:

```text
PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/muse/training/tests/test_web_model.py -q
```

No participant data was read, no fitted real artifact was generated, and no
persistent process was started for this model subtask.
