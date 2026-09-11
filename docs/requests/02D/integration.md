# Phase 2D integration boundary

No dependency/shared-schema change requested. Mount `modules.arranger.api:router` at `/arranger` for bounded local preview/health only. Model proposals, playback preparation, human approval and filesystem export remain explicit local operations; no endpoint starts a provider or audio engine.

`Context.from_summary(summary,composition,groove)` consumes the Phase 2B view and Phase 2C exact canonical records. For modulation use dense local states, not a sparse summary with uncovered request time. Core binds keyboard_damped_v1/bass_pluck_v1/brush_noise_v1 and its own unsynthesized arranger_contact_noise_v1. `render_events` must receive only the pitched/brush partition and the preview label must state Foley excluded. Output transport integration and generic multi-record capability dispatch are future work; do not mark the legacy one-record registry executable.

Approval remains exact-byte/content-hash based. Human tests are distinct from synthetic Approval fixtures. Integration must enforce canonical ControlAction quality, expiry and approved-plan hash before calling the data compiler; no Muse quality decision occurs in arranger. Keep API unavailable from the execution path and retain the active approved plan on candidate failure. Triple/amplitude expressions remain off.
