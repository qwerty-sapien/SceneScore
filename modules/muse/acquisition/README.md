# Phase 2A local acquisition boundary

This module provides raw recording, replay, review tools and a candidate/grammar baseline. It does not train a model or emit audio controls. The live headset/transport remains **HARDWARE_UNVERIFIED**. `python -m modules.muse.acquisition health` reports actual optional-package availability without starting discovery or capture. Run from the repository root with `PYTHONPATH=.:src` and the existing project Python (`.venv/bin/python` in an installed root checkout).

## File replay and synthetic software checks

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition --help
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition record-file private_data/02A/session-01 metadata.json chunks.jsonl --start
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition inspect private_data/02A/session-01
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition replay private_data/02A/session-01
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition replay private_data/02A/session-01 --detect --arm-after-s 1
PYTHONPATH=.:src .venv/bin/python -m pytest modules/muse -q
```

`metadata.json` is a canonical AcquisitionMetadata and each input line a canonical EEGChunk; Phase 1 fixtures demonstrate synthetic input shape, not real data. `record-file` imports recorded records and never relabels them as live acquisition. Replay preserves original numerical values and clock provenance, prints its replay mode to stderr, and streams canonical records to stdout. `--detect` prints canonical candidates/gestures plus raw frontal values, mode, arming, quality and rejection diagnostics. It is an offline unpaced replay, not a clock-mapped physical performance. No EOF synthetic time advance closes an unfinished sequence. `--arm-after-s` explicitly arms once after sufficient warmup, and never rearms following subsequent faults. `--config` accepts a JSON object of `Config` fields, all exploratory and version-hashed. Do not use stdout predictions as labels.

## Optional live route: existing verified LSL stream

The single optional adapter uses an already-running, operator-configured Muse LSL stream. It does not start a Bluetooth daemon, scan arbitrary devices, assume a Muse generation, download a package or launch another process. The user's supported transport/device must first be independently established. No such verification or worn-headset session has occurred in this phase. If pylsl is missing, the command fails explicitly before creating a recording; integrator-managed installation/verification is still required.

Before capture, the operator supplies canonical metadata with the **actually verified** device model, rate, exact channel names/order/units, transport `lsl`, source mode `real_device`, hardware_verified=true and a fresh source-clock epoch. This is an attestation requirement, not an instruction to copy these flags from a fixture. Exact source ID, nominal rate, channel count, XML labels and units are checked; missing/mismatched metadata is refused. Device addresses and source IDs stay local and are not copied into shared reports. A stream nominal rate is not independently measured physical accuracy. Contact-quality information is unavailable in this minimal LSL adapter, so chunks are honestly `unverified` and controls remain disarmed.

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition capture-lsl private_data/02A/session-refit-01 private_data/02A/verified-metadata.json --source-id OPERATOR_VERIFIED_LOCAL_ID --seconds 60 --consent
```

Recording is visible, foreground and bounded to at most 600 seconds per command. Ctrl-C, cancellation, two seconds with no incoming data, a timestamp reset or an exception stops it, closes the inlet, and finalizes the committed raw session. Subsequent reconnect is explicit: restart the command into a **new session directory with a fresh epoch**, verify fit and metadata, warm up, and explicitly rearm the downstream detector. Recovery never replays stale input as live gestures. No automatic reconnect or arm loop hides refits. Stop, rest or adjust comfortably at any time; no straining or prolonged eye closure. No camera capture is implemented.

## Raw format, clocks and privacy

`scenescore.raw-session/1`: a manifest plus one atomically committed canonical JSON file per chunk under `chunks/`. LSL adapter emits single-sample chunks to preserve every internal timestamp hole; this is correct but not throughput-benchmarked hardware storage. Device/source times are stored per sample; the host monotonic receipt denotes arrival of the **batch**, not simultaneous acquisition. LSL source time is not assumed to be Unix, host time or a hardware device counter. No cross-domain alignment is claimed. Timestamp-hole loss counts are explicitly estimates (nearest rate interval); original times/samples remain untouched, and exact packet counters are unavailable. No interpolation, destructive filtering or fabricated IMU is performed. Baseline preprocessing is separate.

Memory is bounded by at most 4096 samples/4 MiB per imported chunk plus fixed detector history. Individual file commits use fsync and atomic replace; recover reconstructs committed chunks and ignores interrupted `.tmp` files. Invalid committed chunks cause failure instead of silent loss. Session directory creation is exclusive; a second recorder cannot overwrite it. There are no global/import-time tasks. Directories use mode 0700, files 0600; persist sessions under ignored `private_data/02A/`. Manifest, labels and export contain private data and must not be sent to GPT or committed. Raw display is intentional local terminal output; avoid shared terminal logging for actual participants.

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition recover private_data/02A/session-01
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition export private_data/02A/session-01 private_data/02A/local-export.zip
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition delete private_data/02A/session-01 --confirm-session-id session-01
```

Export is local only and returns an archive hash, refusing an existing output or output inside the session. Delete requires exact session-ID confirmation and a recognized session manifest; symlink roots are refused. No cloud export or upload is implemented.

## Fault/grammar policy and router

The NEW baseline only consumes enabled AF/FP channels explicitly labelled uV. It uses a 10 Hz causal low-pass and median/MAD robust normalization, retaining both frontal signals. It rejects too-short/long waveforms, uses hysteresis and minimum separation, and labels all scores uncalibrated. Initial warmup 1s, 0.10s minimum inter-blink separation, inclusive 0.5s maximum gap and 0.25s cooldown are **uncalibrated defaults**. A pending waveform delays closure so a third blink never issues a prefix double. Singles/triples and ambiguous trains are rejected; triple/amplitude experiments are disabled. Long trains produce a diagnostic rejection (the frozen canonical count currently stops at three). Decisions record actual observed decision time and closure delay, distinct from future musical-boundary scheduling. No ControlAction is emitted by this module.

Dropouts, changed epochs, stale indices and severe/unverified quality disarm and reset partial grammar; quality recovery requires warmup and explicit arming. Rejected/abstained periods must remain in future evaluation denominators. There is no interpolation, long cooldown trick, intensity/emotion inference or directional thought control.

`modules.muse.acquisition.api:router` exposes read-only GET `/health` and POST `/diagnostics` for an already validated EEGChunk. No raw path browsing or recording starts via HTTP. `health() -> dict` is synchronous and side-effect free. Only the integrator mounts the router under `/muse`; no unbounded stream capability is registered here.

## Muse vertical collection entrypoint

`python -m modules.muse.acquisition diagnose` performs a bounded LSL metadata check
without opening an inlet or reading EEG. Missing `pylsl`/native `liblsl` and absent
streams return structured blockers with exit status 2. A discovered nominal rate
is advertised metadata only. Unknown generation, firmware, channels and units
stay null. Optional transport libraries are loaded only by explicit diagnostic or
capture commands; nothing starts on import.

When the participant is ready, fill a **local copy** of
`examples/collection-protocol.template.json` with their actual consent words,
retention date, pseudonymous participant/refit identity and preassigned role
(`train`, `development`, `final_test`). Mode is `randomized_instructed`,
`natural_activity` or `self_paced`. The blank template is deliberately invalid and
contains no implied consent. Metadata must be canonical AcquisitionMetadata with
verified device facts; no template supplies remembered Muse defaults.

One foreground entrypoint records a bounded session, displays instruction cues,
preserves the protocol and prints raw sample/exposure counts:

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition collect private_data/02A/SESSION metadata.json --protocol protocol.json --source-id ACTUAL_LSL_SOURCE --seconds 60 --start
```

Ctrl-C stops the inlet and closes the session. No simultaneous motor confirmation
is requested. Cues and actual activity remain separate; negative activity exposure
is a protocol assignment until independently reviewed. Contact quality is
unverified on this LSL path, so controls remain disarmed. No data is uploaded.
Remove and refit between separately identified sessions. Use at least three refit
groups to assign independent train/development/final-test roles; this does not by
itself satisfy the empirical acceptance gate.

After collection:

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition review private_data/02A/SESSION
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition confirm private_data/02A/SESSION CUE_ID --performed uncertain --confirmation-s 70
PYTHONPATH=.:src .venv/bin/python -m modules.muse.acquisition label --help
```

`confirmation-s` is a protocol-clock response timestamp, never a predictive
feature or proof of a blink. Confirmations and labels fail while recording is
active. Label actual source-epoch onset/end/final-blink times from independent
observation or delayed review against the raw trace, with reviewer/evidence.
Keep uncertain/disagreement and natural negatives. Review/relabel/export/delete
remain the existing local CLI operations. Deleting the session removes its raw,
protocol, cue, response, label and in-session derived files; separately retained
exports/index/model artifacts must also be deleted or invalidated on withdrawal.

`modules.muse.baseline.replay.replay_session` is a deterministic utility around
the same `CausalBaseline.consume` used by the live adapter. Its explicit initial
arming does not rearm after a fault and EOF never supplies fabricated future
time. `python -m modules.muse.acquisition.examples.synthetic_replay` demonstrates
one accepted synthetic double and removes its temporary raw fixture at exit.
