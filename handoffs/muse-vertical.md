# Muse vertical handoff

Local implementation status is PIPELINE_TESTED_ONLY. The approved static demo is live at https://scenescore-muse-vertical.vercel.app. Read [the execution gate](../reports/muse-vertical/GATE.md) for evidence and remaining hardware/training limits.

## Run the prepared local demo

From the repository root:

```sh
make muse-demo
```

This builds the browser and starts bounded web/companion processes for ten minutes. Open http://127.0.0.1:8771 and choose **Start blink demo**. The explicit draft stays unapproved. The simulator works directly through the common music dispatch path.

For the full synthetic raw-EEG path, copy the ephemeral companion token printed by the launcher into **Local companion & detector**, connect, select the simulated source, wait for warmup and clock calibration, then arm. A generated double-blink waveform occurs every eight seconds; the real causal software pipeline closes it and can request a musically valid change. The initial seek selects a scene interval with signed motion. Late requests with no remaining musical boundary are correctly suppressed. Ctrl-C stops both exact process groups; automatic expiry also stops them.

This source is SYNTHETIC_TEST. A disconnected or unverified source cannot become LIVE_MUSE through a dropdown. No raw recording occurs in the companion. See [companion documentation](../services/bridge/README.md) for raw-session replay and the optional exact-source LSL command.

## Participant training step

`make muse-diagnose` returns current transport blockers without capturing EEG. Headset availability and type are pending the user's answer. Do not fill consent or hardware verification fields from fixtures.

Follow [acquisition instructions](../modules/muse/acquisition/README.md) using a local copy of the blank protocol template. Collection is explicit, foreground and bounded; cues, delayed feedback and independent labels are separate. Separate refits must be assigned before comparison, and actual labels need independent observation/review. EEG stays in ignored private_data/02A.

[Training instructions](../modules/muse/training/README.md) explain frozen assignments and readiness auditing. With eligible data, this integrated command audits the complete split before creating a train-only numeric quality profile:

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.training --data-root private_data/02A --index private_data/02A/split.json --quality-profile-out private_data/02A/quality-profile.json
```

That command calibrates signal validity, not a learned blink classifier. The bounded research model functions still require real comparison, preregistration, held-out evaluation and artifact validation. Zero real models or profiles were produced in this task. [Quality semantics](../modules/muse/runtime/QUALITY.md) explain the hardware binding and contact-not-measured scope.

## Resume remaining work

The 5 ms mapped request-to-browser gate failed at 9.64 ms in the final software observation. Preserve the timing evidence and inspect transport/scheduling with the same definition; do not subtract closure or musical wait to disguise it. Physical blink/output measurements are absent. No performance or human audition approval was fabricated.

The user approved the exact 14-file, 25.8 MB payload in the [manifest](../reports/muse-vertical/deployment-manifest.json). It is deployed and verified; see [deployment evidence](../reports/muse-vertical/deployment.json). Choose Start blink demo, allow the animation to begin moving, then Simulate accepted double blink. The remote semantic simulation changed C to B-flat while retaining approval:null. A first-frame stationary request correctly holds the key. Actual HTTPS-to-loopback companion behavior remains unverified. The working tree is concurrently evolving under separate Blender/music tasks; rebuilding changes the reviewed payload and requires fresh integrity evidence.

Scoped worker notes: [acquisition](muse-01.md), [runtime](muse-02-04.md), [surface](muse-05.md). The integrator preserved all integrated source. No task-owned service remains running.
