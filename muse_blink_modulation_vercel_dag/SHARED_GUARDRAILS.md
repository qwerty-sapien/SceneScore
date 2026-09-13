# Shared guardrails — blink-to-control vertical

Every node obeys all of these. A node may add constraints; none may relax one.

## Authority and truthful evidence

`AGENTS.md`, `docs/VISION.md`, `docs/CONTRACTS.md`, `docs/EVALUATION.md`,
`PARTICIPANT_PROTOCOL.md` and the user's current instruction outrank this pack. Where this
pack and a repo document disagree, the repo document wins and the conflict is recorded.

Never train on synthetic fixtures and report the result as real performance. Never present
schema validity, a passing test, a hash match or a model's opinion as detection accuracy,
hardware validation or human verification. Distinguish passed, failed, blocked and not run.
Mark `real_device`, `replay`, `synthetic` and `keyboard` as independent provenance
dimensions. Unavailable measures are null with a reason, never a fabricated zero.

Do not claim 99–100% from a hackathon dataset. Report the complete causal pipeline
including upstream candidate misses, grammar rejections and quality abstention — not the
classifier in isolation.

## What this system is

An ocular-gesture control for a music instrument. It is not a mind reader, not a
mental-state detector, not an emotion classifier and not a diagnostic device. No EEG
feature is stored, displayed or described as a health, cognitive or affective indicator.
There is no directional thought control: geometry supplies the motion policy, and the
gesture requests a discrete prepared action.

Natural blink clusters can resemble deliberate gestures. There is no guaranteed intent
inference, and the UI must not imply otherwise.

## Scientific hygiene

Never use cue timing, button presses, labels or soundtrack state as predictive features.
Split complete sessions and refits before windowing. Freeze preprocessing, threshold, model
and grammar before the final replay. No final-test tuning, no detector-generated truth, no
leakage from overlapping windows.

Preserve raw EEG and timestamps unmodified. Use causal preprocessing for anything claimed
to work live; an acausal filter that peeks forward is not a live result no matter how good
its offline score is.

Keep a deterministic baseline and a small supervised model before considering anything
more complex. Complexity earns its place on held-out real replay or it does not ship.
Preserve the attributed RAGTM comparator; it is a comparator and must never issue a
control.

## Gesture discipline

Deliberate double blink is the only required gesture. Triple-blink and amplitude-derived
controls are experimental and disabled per `docs/VISION.md`; do not enable them here.

Closure before commitment: emit nothing until the sequence is closed under the double-only
grammar. A triple never produces a double plus a triple, and never produces a double.
Reject ambiguous trains rather than emitting and retracting. A rejection is never retracted
by a later emission for the same blinks.

Dropout, reconnect, quality failure, refit and model reload each clear partial gesture
state and require warmup and re-arm. Music continues unchanged while controls are
suppressed.

## The seam

`INTERFACE_CONTRACT.md` binds every node here. Raw EEG never crosses into the music
engine; the music engine receives a small semantic `ControlAction`. This pack does not
choose a key, a chord, a voicing or an arrival boundary, and does not compute
`signed_semitones` — the approved plan's motion policy does that.

No network call, model inference or LLM sits between an accepted blink and the musical
action. The four sources — live, replay, synthetic, keyboard — construct the same record
and pass the same validation.

## Latency honesty

Report the ladder intervals separately, per `examples/latency_ladder.json`. Sequence
closure delay is real, is disclosed, and is not hidden inside a headline number. "Sub-300
ms" may describe only accepted control to scheduled audible onset. A scheduled onset is not
an acoustic onset. Device and audio clock domains cross only through a validated
`ClockMapping`; a stale mapping is an error.

## Deployment truth

A serverless deployment cannot hold a persistent Bluetooth or LSL process. Do not pretend
otherwise, and do not architect around the pretence. The deployed surface must be useful
without hardware — replay recorded sessions, simulate an accepted event, exercise the real
music-control contract — and must label `live`, `replay` and `simulated` explicitly and
visibly. Rendering a replayed or simulated event as live is a truthfulness defect, not a
UI detail.

If a local companion bridge is chosen, bind it to loopback with a bounded authenticated
handshake and narrowly scoped commands. Do not expose it to the public internet. Raw EEG
stays local by default; the deployed app may hold non-sensitive configuration and model
metadata only.

## Ownership

Each node writes only the paths its prompt lists, plus its own handoff and
`docs/requests/<node>/`. `apps/web`'s shared shell belongs to the music pack; this pack
adds its own subtree and sends scoped requests for shell changes. Shared schemas, root
locks and evaluation thresholds belong to the integrator. Parallelize only with genuinely
disjoint write scopes.

## Resource discipline

Record the exact identity of any persistent capture or bridge process, terminate its
children and verify exit before finishing. Never kill unrelated jobs. Do not add heavy ML
dependencies to the root locks; the repo deliberately installs none of RAGTM's stack.
