# 0012 — Direct local blink-training workspace

Authority: the user's 2026-09-13 request for a webpage to collect their live EEG,
label intentional blinking with B, and directly train a model using the RAGTM
webpage as a reference. This authorizes a new capture/training UI and its local
service. It does not supply actual consent words, device facts or measurements.

The supplied RAGTM EEGStreamingPage was inspected read-only. Its useful reference
is device selection, stacked EEG time series, blink state and explicit capture.
Its game code, automatic uploads and filtered-only CSV behavior are not imported.

Visual thesis: a calm, warm-white laboratory workspace, dark ink, one teal accent,
with stacked live traces as the dominant visual.
Content plan: connection strip; live signal and current trial; session review;
local model training and test result. Each section provides an operational action.
Interaction thesis: smooth rolling traces, a restrained B-held interval highlight,
and explicit recording/review/training state transitions with reduced-motion support.

Default command gesture remains a deliberate double blink. Singles, natural activity,
triples and movement are recorded as comparison/negative trials. B-down/up creates
an intent marker in a separate stream, not an exact physiological label or model
feature. Guided cues permit hands-free blinking. Include keypress-only negatives to
check motor/timing confounding. After recording, the user reviews raw waveforms,
adjusts the actual interval and confirms its class or leaves it uncertain.

The new model is a bounded personal, causal two-second-window classifier trained
only on reviewed whole training-session examples. It predicts deliberate-double
windows versus reviewed other activity. It is experimental and separate from the
existing causal candidate/closure pipeline; there is no automatic music authority.
Development examples are whole sessions/refits and are excluded from fitting.
Window-level held-out results are not event recall or false activations per hour.
No reviewed real samples means no real fitted model. Synthetic rehearsal is visibly
separate and cannot be mixed into a real model or certify hardware.

The service binds only 127.0.0.1:8767, with an explicit token, exact Origin/Host,
bounded recording, messages, samples, requests and model work. It does not start
recording, discovery or headset streaming on import. The page starts/stops an
existing selected LSL stream only after user action and live-processing consent.
Record requires separate local-storage consent. Raw samples retain source clocks,
units, gaps and provenance in ignored private_data/02A/training-web. Browser traces
are local display; no EEG, labels or models are uploaded. Training and publication
are separate operations. Existing immutable prompts/schema/locks remain unchanged.

Real transport and model quality must be validated with the user's actual headset.
Missing runtime/stream/device metadata is a visible blocker, never a synthetic
stream presented as live. All task-owned test processes stop before handoff.
