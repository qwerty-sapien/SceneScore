# Calibrated numeric signal quality

`QualityGate(metadata, profile_dict_or_None).consume(chunk)` returns canonical
`{state, reason}` quality. Missing calibration remains `unverified`. No UI boolean
can supply a profile. A profile is a local module-versioned JSON artifact, with
an exact content digest and hardware/config binding. `reset()` clears rolling
windows and continuity; it supports a valid midstream sequence/index afterward.
`status(now_host_s, host_epoch)` is required on the bridge timer when no samples
arrive so a silent device cannot retain good quality indefinitely. It compares
host receipt to host monotonic only, never host to device time.

With a valid profile, the gate checks finite samples, channel names/order/units,
verified rate, exact acquisition configuration, absolute amplitude, rolling
variance, flatline range, sequence/sample continuity, intra-chunk timestamp gaps,
epoch changes and host receipt staleness. Every window uses current/past samples
only. Bad upstream quality always wins. A failure clears rolling calibration
state; the bridge must also disarm the detector and require explicit rearm after
detector and quality warmup. The gate starts no jobs, reads/writes no files and
never modifies raw input chunks. The bridge replaces quality on a separate copy
used by its detector; raw recording stays untouched.

`good` means **calibrated numeric signal checks passed**. Its reason explicitly
says `contact_not_measured`. This is not electrode impedance, contact quality,
health, EEG accuracy, blink accuracy or intent detection. The profile's declared
scope is exploratory numerical signal validity. The absence of impedance data
therefore remains visible without making the software path permanently unusable.
Real capture still needs consent, verified transport metadata and real training.

Profiles bind device model, transport, channels/units/enabled flags, sample rate,
hardware-verification state and acquisition config SHA-256. Session and clock IDs
are deliberately excluded from the hardware binding so a calibrated device can
be used in a new session; every stream still undergoes its own session/epoch
continuity checks. Changing any bound hardware/config field requires a new
profile. Synthetic calibration never certifies `real_device` acquisition.

`calibrate_profile(metadata, sessions, config=None)` computes the artifact using
training data only. Each supplied session contains `metadata`, exact `chunks`,
independent `labels`, `role:'train'`, `content_sha256` of those first three fields
using `quality.digest`, and `consent_ref`. Real sessions require verified
real-device metadata, a consent reference, independent observation/review label
sources and actual reviewer identifiers. Synthetic labels are allowed solely
for synthetic software tests. Content changes and development/final-test roles
are refused. The outer training command must first run the existing full-split
audit to prevent refit/session leakage.

The frozen `train-window-extrema-v1` policy uses nonoverlapping 0.5-second
training windows across continuous chunks. Dropout and explicitly bad-quality
chunks reset/exclude affected windows. Complete flat windows make calibration
fail instead of silently declaring flat EEG usable. Bounds are computed per
enabled channel: maximum observed absolute amplitude times 1.5; minimum
observed variance times 0.1; maximum variance times 4; minimum observed window
range times 0.01 for the flatline threshold. These explicit factors are
preregistered software choices, not calibrated claims of false-positive rate.
All training windows include blink waveforms where present, avoiding a gate
trained only on quiet EEG that would systematically suppress intended blinks.
Receipt staleness defaults to 0.5 seconds; allowed device gap is 1.5 sample
periods. Config is versioned, finite, bounded, and included in the artifact hash.
Train-only alternate config must be frozen before evaluation. No online updates.

The artifact records exact raw-session/metadata/label hashes, session IDs,
reviewer/source and consent references; it contains no raw samples. Its digest
detects accidental changes and binds lineage; it is not a signature or an
independent attestation that a participant or reviewer existed. Those facts
come from the existing audited local training records.

Integrated audited calibration CLI:

```text
python -m modules.muse.training --data-root private_data/02A --index private_data/muse-training-index.json --quality-profile-out artifacts/muse/quality-profile.json
```

The command first audits the complete frozen split, then loads only train
sessions and computes the profile from preserved raw bytes. Output creation is
exclusive. No threshold editing or UI quality override is required. This command
calibrates signal validity; it does not claim a learned blink model was trained. Evaluate the frozen profile on held-out
whole-session replay together with the blink detector, counting gate abstention
and rejected gestures in the full denominator.

The live companion consumes the generated file with
`--quality-profile <output-directory>/quality-profile.json`. Profile absence,
wrong hardware/provenance, stale streams, bad signals and warmup remain visible
and suppress new controls while music continues. Neither this work nor its
synthetic fixtures constitute a real-device calibration or deployment gate.
