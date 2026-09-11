# Phase 3B: integrate one complete performance before expanding scope

Prerequisites: phase 2B-2E handoffs and either the real Muse baseline or a clearly labelled replay/keyboard adapter from phase 2A. A newly trained detector is optional. Read AGENTS, all handoffs, VISION, CONTRACTS and EVALUATION. You are the integrator and may reconcile shared schemas, root locks, service mounting and cross-module tests through recorded decisions. Preserve worker commits and avoid broad rewrites.

## First vertical slice
Load the hero scene and matching sidecar -> exact catalogue lookup of Tilted Blue and a light brush groove -> baseline mapping or approved GPT plan -> deterministic audio playback -> one double-blink/keyboard modulation -> exported mix/performance log. Complete this before adding all ten scenes, every model, triple gestures or a live editor.

Start with replay and keyboard to expose integration failures independently of hardware. Then connect the real headset without changing downstream action semantics. Use the best frozen real-data detector available, including a simple baseline when it performs better. Source changes are explicit in the UI and log.

## Clock and identity reconciliation
Trace one real control end to end: original sample index/time -> candidate -> final blink -> detector decision -> bridge receipt -> requested transport position -> scheduled musical boundary -> rendered note change. Display these distinct delays. Use handshake/offset estimation between monotonic clocks where necessary; never equate Python monotonic time with browser performance time by numerical value.

Trace one visual contact: evaluated scene time -> interaction event -> exact Foley schedule -> displayed video time. Confirm frame origins, fps/base, loop durations, encode offsets and audio output latency are handled. Separate scheduled offset from measured audiovisual offset. Reject stale sidecars and mismatched media hashes.

Deduplicate event IDs and bound queued controls. On pause/seek/refit/reconnect, clear partial gestures and stale transport generations. No missed gesture queue should discharge after reconnection. A Muse failure leaves the current composition playing.

## Human approval and demonstration
Provide scene/score selection, rule inspection, candidate plan diff, short audition and approve/reject. Freeze a plan plus its approved modulation family. The performer may then blink without an approval modal. A new plan cannot silently replace a playing one. New scene variants invalidate affected caches.

The visible demonstration is:
1. Play a short silent animation.
2. Add the original groove and baseline phrase.
3. Enable scene-aware anticipation, collision accents and separation release.
4. Trigger a double-blink that requests a visible, musically timed key change while volume/articulation stay unchanged.
5. Select the matched near-miss variant, showing changed music and absent collision Foley.
6. Export the played performance and show which inputs/plans/controls produced it.

This is animation, not a game. A judge does not need a headset for the demo to remain understandable. No unverified inference about emotions, focus or stress belongs in the UI or pitch.

## Export
Resolve the complete performance log to the same symbolic event sequence used by live playback. Produce a stereo audio file, separate stems, score/control log, arrangement/scene hashes and a muxed video where a verified local encoder is available. Handle source/output duration, tails, sample rates and video timestamp offset explicitly. A fallback audio-plus-video bundle must be labelled when muxing was not performed.

## Integration tests and resource management
Run scene contract checks, music tests, model/replay tests and browser tests from a clean local start. Exercise no network, no API key, API timeout, unavailable samples, stale cache, invalid JSON, dropped stream, bad quality, duplicate/out-of-order events, excessive controls, rapid pause/seek, audio context suspension and unknown groove/model IDs.

All degraded paths must preserve the active performance or give an actionable recovery. Do not silently fake success. Keep raw EEG private and service binding on localhost with appropriate local-origin restrictions. No secrets in frontend bundles or logs. Limit render and training concurrency while capturing EEG or playing the demo.

Report peak levels, scheduled/observed timing, event correctness, real-source provenance and human audition status separately. Do not let a green test suite imply musical quality or empirical detector reliability.

## Exit gate
A documented one-command replay demo and an actually exercised live-Muse path when hardware is available; one complete exported performance; correct default gesture behaviour; approved arrangement and provenance; no schema drift; explicit remaining limitations. The core remains demo-ready with network/headset loss. Cut stretch goals before modifying tests to hide failures.
