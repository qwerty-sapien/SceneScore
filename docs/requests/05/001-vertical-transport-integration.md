# Node 05 → coordinator: opt-in transition transport integration

The new model/table API is prepared in this isolated worktree. This request does
not modify shared transport, engine, UI, schemas, locks or approvals. The existing
`transition()` and its frozen golden remain unchanged.

## Constructor and unlock

Build `bundle.music_vertical` using Python
`modules.music.transitions.vertical_transition_sidecar(source['eligible_arrival_ticks'])`.
The source is node 02's exact `build_vertical_score()['sidecar']`, with eleven safe
internal bars from 2.5 through 27.5 seconds. The versioned sidecar must be included
in preparation provenance/cache identity and the exact candidate reviewed by the
human. It is not a replacement for canonical plan approval.

`prepareVerticalTransitions(bundle, plan)` validates the sidecar/table identity,
constant 4/4 tempo, complete duration, non-terminal increasing bars, at most 48
arrivals, and node 02's maximum four-second coverage gap. It solves all 216 MIDI
voice paths before playback and prebuilds only approved default ±2 programs.
Jazz has no activation path in this edition, including when an environment flag
is accidentally set. A future named human audition/decision needs a deliberate
versioned implementation amendment.

Prepared fields are:

- `entries`: 216 immutable voiced table entries, indexed by tier/tonic/sign/lead.
- `programs`: immutable arrival/entry programs, at most 12 score events plus two
  acknowledgement notes each; no new program is allocated during selection.
- `variants`: original affected event ID to cached MIDI-pitch variants within the
  plan's register; `variant_origins` resolves cached variants to their source ID.
- `acknowledgements`: flat references to prebuilt two-note, ≤60-velocity dyads.
- `arrivals`, `bar_seconds`, `initial_tonic`, `affected_ids`: bounded lookup data.

Prepare all program, variant and acknowledgement sound buffers before playback.
Deduplicate pitched waveforms by sound parameters rather than event ID to keep
buffer memory bounded; the parent owns `Engine.key` and its memory audit.

## Accepted action and acknowledgement

Keep all existing `Timeline.submit` validation, deduplication, clock, plan,
quality, expiry, and single-pending checks. Use the action's supplied signed
semitones unchanged. Then call:

```ts
const program = selectVerticalTransition(
  prepared, currentTonic, action.signed_semitones!, sceneNow,
  sceneNow + action.expires.seconds - audioNow,
);
```

It returns an existing program reference or `undefined`. It inspects at most 48
declared arrivals and three fixed lead choices; keyed table/program access is
O(1). Earliest feasible arrival wins, followed by the largest declared lead that
fits actual headroom. The conservative default margin is 175 ms. A table row's
declared `lead_bars` is honoured even when its `lead_ticks` is shorter. Expiry is
exclusive. No feasible program means `no_feasible_boundary_before_expiry`.

Schedule both prebuilt acknowledgement buffers at receipt +20 ms, with no whole
score traversal, copy, buffer synthesis, voice search, or recompilation between
acceptance and scheduling. Preserve all gain/articulation/expression controls.
If acknowledgement scheduling fails, cancel the pending program; active tonic
and original events have not been mutated.

`program.start_s` begins the progression, `arrival_s` is the declared safe bar
and established new key, and `end_s` ends a quarter-bar landing. For the vertical
mode, the seam's `Decision.boundary_s` should identify `arrival_s` (t6); record
progression onset separately. Active tonic changes only when arrival executes.
Do not change legacy timing semantics to retrofit these opt-in fields.

## Fill, cancellation and export

At progression start, end only sounding bass/harmony sources. Use
`isVerticalVoice` rather than testing merely `midi_pitch !== null`. Never clear
lead, object, brush or Foley notes in the accepted path.

Within `[start_s,end_s)` the program owns its four harmonic lanes. Schedule the
prepared slot events; suppress overlapping original events in those lanes.
Outside the overlay, apply each completed program's signed step to the current
event: `verticalPitchVariant(prepared,currentEvent,program.entry.signed_semitones)`.
Version 2 preserves octave history; the third argument is exactly +2 or -2,
never an absolute tonic. Full prepared events return cached references.
`clipVerticalEvent` and `verticalEventFragments` are fill/export helpers for
half-open note intervals. In-memory fragments retain source identity for successive
programs through export-only weak bookkeeping; they preserve their clipped timing
when transposed again. Rebuild exports from the original score and recorded program
history after serialization, rather than treating serialized fragments as prepared
source events. A crossing sustain is kept up to the overlay and
resumed after it, with exact scene-time continuity and preserved independent
properties. Unaffected lanes retain the original object reference. Program
phrasing overrides a near-miss hold once and explicitly lands at the new tonic;
the single-pending transport rule prevents unresolved programs from stacking.

Do not invoke clipping/export compilation before acknowledgement scheduling.
The engine may iterate the existing fixed-budget score during fill; its accepted
path must only touch the bounded pending program and active-node set. Build the
full editable performed score from the exact program history outside the
accepted path. Include acknowledgements in that export or clearly identify them
as a separate recorded control-audio stream.

Pause/seek must cancel pending controls and their overlay scheduling consistently.
Before arrival the tonic remains the old tonic. After arrival the performed
history records the new tonic. Keep the exact human approval gate, visible source
mode and all existing no-bypass behavior.

## Remaining integration checks

The owning model/table checks pass, including all 216 actual voice paths,
24-event bound, preserved lanes, note splitting, lead choices, strict expiry,
two modulations, near-miss hold resolution, frozen bytes and legacy goldens.
Coordinator tests still need to exercise the actual `Engine.submit` fake clock
for two scheduled acknowledgement sources at +20 ms, no score traversal or
recompilation before acknowledgement, active tonic only at arrival, cancellation
and sequential program export. This worker has not claimed acoustic latency,
human approval/audition, or the entire node 05 end-to-end gate.
