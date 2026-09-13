# Coordinator — blink-to-control vertical, six hours

## Goal

A deliberate double blink, detected from this owner's real Muse signal by a causal
pipeline, closed under a double-only grammar, emitted as exactly one `ControlAction`, and
turned into an audible harmonic response by the music engine — with every interval on the
latency ladder measured separately and reported honestly.

One claim must survive an unfriendly reviewer: *that blink caused that key change, and
here is what we actually measured, and here is what we did not*.

## The architecture boundary that shapes everything

A serverless deployment cannot own a persistent Bluetooth or LSL process. Acquisition is
local. The deployed surface is the training protocol, the feedback loop, the replay and
diagnostics view, and the music demo — and it must stay useful and visibly honest with no
hardware attached. Node 00 picks the least fragile verified route between them: a loopback
local companion, or direct browser BLE **only** if support is proven on the actual target
browser and headset in this environment. A replay fallback exists either way.

## What this pack does not own

The harmonic transition. The chord voicings. The arrival boundary. `signed_semitones`.
Those belong to the music pack and to the approved plan's motion policy. This pack decides
*when*; the scene decides *which way*; the frozen table decides *how*. Read
`INTERFACE_CONTRACT.md` — byte-identical in both packs — before assuming you may touch
something on the far side of the seam.

## Why the seam is frozen first

Node 01 comes before the detector work, which is the main structural change from revision
1. Freezing the `ControlAction` boundary and the latency ladder early is what lets the
deployed surface (05) and the music dispatch (06) proceed in parallel with detector work
(02, 03, 04) instead of waiting on it. It also prevents the failure where three nodes each
invent a slightly different event shape.

## Detection objective

Very high deliberate-double-blink recall with extremely few false activations during
ordinary blinking and activity. Evaluate the complete causal pipeline, not the classifier
alone: candidate misses, grammar rejections, quality abstention and refractory periods all
count.

Closure delay is a floor, not a bug. Under double-only grammar, a decision cannot commit
until no third blink has arrived within `max_gap_s` — 500 ms at the current config,
leaving 250 ms of headroom under the repo's 750 ms p95 gate. Raising `max_gap_s` above
0.73 s makes that gate unreachable regardless of classifier speed. Emitting on the second
blink to save latency converts every triple into a false activation and is forbidden.

## Honest end state

`docs/EVALUATION.md`'s `SUPERVISED_DEMO_READY` requires evidence six hours cannot produce.
Plan for `PIPELINE_TESTED_ONLY`, or `REAL_DATA_EXPLORATORY` if a consenting participant is
genuinely available under `PARTICIPANT_PROTOCOL.md`. Export the label the data supports.

## Execution

00 freezes lineage and architecture. 01 freezes the seam; 02 starts acquisition in
parallel. 03 builds the detector ladder on 02's real contracts. 04 collects and freezes
evaluation. 05 and 06 proceed from the frozen seam in parallel with 03 and 04. 07 is the
end-to-end gate on the exact demo path.

Repairs route to the owning node and rerun affected downstream gates. Three attempts per
gate, then report the failure honestly.

## Success gate

A worn headset produces one semantic event per deliberate double blink; a minute of
natural activity produces no event storm; a dropout mid-gesture clears state and requires
re-arm; the accepted event reaches the identical music path that keyboard simulation
reaches; and the ladder intervals are reported separately with exposure denominators
stated. If live hardware cannot be completed, leave a precise blocker and a convincing
replay demo that is not called hardware-validated.
