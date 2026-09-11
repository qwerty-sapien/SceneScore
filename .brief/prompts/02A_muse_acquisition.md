# Phase 2A: real Muse capture, labels, replay and the preserved baseline

Prerequisite: phase 1 contracts are frozen. Read AGENTS, VISION, the blink-evaluation skill, CONTRACTS and EVALUATION. Own `modules/muse/acquisition/`, `modules/muse/baseline/`, `modules/muse/annotation/`, module-local tests and `handoffs/02A.md`. Do not alter shared schemas, browser UI, audio, root lockfiles or Blender code. Expose the agreed router/CLI interface for later mounting.

## Objective
Produce genuine, timestamped, privacy-preserving Muse recordings and trustworthy gesture annotations. Deliver a causal baseline and exact replay before pursuing complex models. An agent cannot perform the owner's blinks or manufacture the resulting data.

## Inspect and preserve RAGTM
Use the phase 0 lineage report and `RAGTM_PATH`. Read and preserve the actual previously successful acquisition and blink logic. Package its relevant logic behind the new adapter with its original parameters and version recorded. Test behaviour equivalence on real replay when recordings exist. Preserve its dependency/licence information. Do not modify the original repository or bring over game UI.

If unavailable, implement an explicitly NEW deterministic baseline. Never label it the old RAGTM detector. Report what still needs code comparison.

## Hardware and stream
Verify the precise Muse generation/board and supported transport on this Mac. Prefer the proven original transport when available; otherwise test a compatible BrainFlow adapter. Do not guess board/channel indices, units or sample rate. Do not require browser Bluetooth as the only route. Support exactly one functioning live transport initially plus file replay and synthetic fixtures.

Record original numerical samples without destructive preprocessing, sequence/sample indices, actual rate, units, channel names/masks, source/device time if present, host monotonic receipt time, packet gaps, quality and optional IMU. Device timestamps and host timestamps have distinct semantics. Derive sample times explicitly; never assign every sample in a received batch the same time. State timing accuracy limits.

Use a local chunked format with a versioned manifest and separate label/event JSONL. Persist cleanly on disconnect, maintain bounded memory, and make recording recoverable. Keep raw data, names, device addresses and optional video outside git and cloud requests. Use pseudonymous participant/session IDs. Recording must be visible and explicitly started by the user. Provide deletion and export controls.

On disconnection or severe quality loss: reset partial gesture state, suppress new commands, keep the soundtrack running, display the cause and reconnect without replaying stale events. Refit/reconnect requires warmup and explicit re-arming. Never infer new blinks by interpolating missing packets.

## Acquisition/annotation interface
Provide a small module-owned local capture page or CLI independent of the production web UI. Show raw frontal channels when available, candidate markers, stream quality and clock diagnostics. Modes: natural activity; randomized instructed gestures; self-paced gestures; review/relabel; real replay; synthetic software test.

The cue records requested intent, not the actual occurrence. After each trial allow confirmed performed/missed/uncertain labels. Mark actual blink onset/end or sequence completion through review. Optional local webcam timing is permissible only with consent and never required or sent to GPT. No detector prediction may automatically become evaluation ground truth. Keep cue timestamps, user responses and prediction data separate.

Avoid simultaneous keyboard labels that could teach the detector hand/head movement artifacts. Use delayed confirmation or later review. Cue content/timing and game/audio feedback are not model features.

## Proposed preparation protocol
Use comfortable voluntary gestures, normal rest breaks and a stop control. Do not ask the user to strain or hold their eyes closed for long periods. Begin with a short comfort/fit check, then collect multiple independent sessions with the headset removed and refitted between sessions.

Across preparation, aim for 200-300 verified deliberate double-blink examples and at least 60-120 minutes of varied natural activity if practical, distributed across sessions rather than one continuous fit. These are data collection goals, not a requirement to exhaust the participant or a guarantee of near-perfect accuracy. Leave one or more sessions untouched for final evaluation.

Include natural single/double blinks, reading, watching the animation, speaking, smiling, looking around, head turns, jaw activity, gentle headset adjustment, quiet rest and ordinary blinking. Include self-paced deliberate gestures so the model does not depend on a predictable cue rhythm. Include triple sequences only for the optional experimental profile. Annotate ambiguous spontaneous clusters separately and include their false-activation impact in free-running tests.

## Causal baseline
Retain a blink-sensitive path. Do not run an ocular-artifact-removal pipeline that deletes the target signal. Evaluate a causal low-frequency filter and robust baseline normalization appropriate to the observed stream; choose settings through held-out development data, not a remembered universal amplitude threshold.

Use frontal channels and optional temporal/IMU context according to measured channel availability. Do not blindly subtract correlated frontal channels or common-average away the bilateral blink. Features may include amplitude relative to baseline, waveform duration/slope/area, channel agreement, saturation and motion flags. Preserve sign convention and latency information.

A two-stage baseline detects candidate blink waveforms, then uses a finite-state grammar for gestures. It needs hysteresis, waveform de-duplication, minimum separation, configurable inter-blink gaps, sequence closure and a bounded cooldown. Initial timing values are exploratory and must be calibrated. Do not hide missed gestures with a long cooldown.

For double-plus-triple mode, wait for the sequence-closing interval after the second blink. A third accepted blink changes the sequence class before commitment; execute exactly one action. Default double-only mode should still reject overlong/ambiguous trains under its documented grammar. Distinguish last-blink-to-decision latency from first-blink-to-decision and decision-to-musical-action delay.

## Exit gate
Deliver real capture/replay commands, annotation workflow, untouched raw-data format, baseline adapter, stream fault tests and a short genuine recording when the owner has provided one. If no hardware session has occurred, report `HARDWARE_UNVERIFIED` and stop at the working recorder/test-fixture boundary. Do not claim trained accuracy. Handoff includes the exact command for phase 3A and any remaining human acquisition actions.
