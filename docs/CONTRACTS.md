# Shared contract semantics — frozen version 0.1

Phase 1 implements JSON Schema 2020-12 at `contracts/0.1/schema.json`, generated TypeScript at `packages/contracts/generated.d.ts`, and Python/TypeScript conformance against identical synthetic fixtures. See ADR 0002 for serialization, reference checks, implementation limits and the freeze baseline. A conservative provider projection is present; its live provider compatibility is unverified. Stricter local semantic validation remains authoritative.

## Common envelope and conventions
Every artifact records schema name/version, stable ID, source mode, creator/tool/config/input hashes and seed when applicable. References resolve to exact IDs and versions; unknown references, incompatible major versions, non-finite values and unit ambiguity are errors. Hash exact persisted bytes with SHA-256; hash-bearing approval excludes its own digest and uses the documented serialized payload. Phase 1 must settle serialization before hashing fixtures. A change affecting meaning or required fields needs migration, fixture updates and an integrator decision; no silently diverging schemas.

Times use seconds with named clock domains/epochs, never implicit wall clock; diagnostic latencies use ms. Raw sample indices are monotonic per continuous stream segment with explicit gaps. UTC is provenance. Scene time zero is declared start frame: `(frame-start_frame)*fps_base/fps`; support subframes and rational fps. Export world-space right-handed XYZ, Z up, metres, m² surface area, optional m³ volume, m/s velocity, m/s² acceleration. Quaternion order is xyzw; matrices are row-major storage acting on column vectors. Browser conversion must be explicit and tested. Unavailable measures are null with reason, never fabricated zero. Geometry operates on evaluated meshes after modifiers/transforms, not object origin metadata alone.

## Schema families
| Schema | Required meaning and invariants |
|---|---|
| AcquisitionMetadata / EEGChunk | Session, headset/transport/config, channel names/mask/units, verified sample rate Hz, sequence/sample indices, device timestamp, monotonic receipt, clock epoch, dropout/quality, optional IMU with units. Preserve untouched raw samples locally; conversions recorded separately. |
| BlinkCandidate | Candidate ID, session/source/model version, onset/end and clock, score with score type, quality; never itself a control or truth label. |
| GestureEvent | Linked candidate IDs, gesture count, onset/end/final-blink/decision times, source, grammar/parameter hash, confidence semantics, accepted/rejected reason. Explicit closure delay; a triple never emits a double plus triple action. |
| ControlAction | Unique action ID, originating gesture, epoch, request/decision time, eligible boundary/expiry, signed transition and scene-policy evidence, approval hash, queued/executed/suppressed state and reason. Default changes harmony only and preserves gain/articulation/expression. |
| SceneManifest | Source/render/generator/config hashes, seed, fps/base, start frame/duration, units/axes/quaternion/matrix conventions, camera and persistent object IDs. Source/video/sidecars refer to the same generation. |
| ObjectState | Object ID, scene time/frame, evaluated world transform, mesh-derived area, bounds and velocities where defined; derivative method and sampling interval. Volume only for valid geometry. Stable sonic identity across loops/key changes. |
| InteractionEvent | Stable unordered pair ID (no self-pairs), event-instance ID, onset/duration, centre distance distinct from signed surface gap, relative normal/tangential speeds, contact method/uncertainty. Label analytic/scripted/baked/heuristic; proximity is not physical impact. Impulse null unless supported. Near miss needs independent positive-gap evidence. |
| CompositionSpec | Exact composition/version, PPQ=960 default, meter, tempo/key/harmony maps, form length, unswung quarter-note ticks, C4=MIDI60, pitches/velocities 0–127, positive durations, separate control lanes. Extensions above 12 semitones are voicing inputs, not discarded pitch classes. |
| BrushGroove | Exact id AND version, meter/PPQ/length, unpitched flag, technique/hand/velocity/duration, swingable flag, recipe/sample identity and humanization seed/bounds. Never transpose. Unknown groove is an error. |
| ScoreEvent | Unique event/lane/object/plan IDs, ticks plus materialized resolved times, note/voice or unpitched action, articulation/dynamics/ornament separately, swing-applied state. Apply swing only once to eligible events using composition's selected policy. Bounded register and signed interval separate from tonic pitch class. Foley references scene seconds rather than quantized ticks. |
| AudioAssetManifest | Asset/stem IDs, content hash, sample rate Hz, channels, duration, source/license, pitched flag, synth/recipe version, peak measurements and common timeline origin. A MIDI file is not evidence of audible output. |
| ArrangementPlan / Approval | Input hashes, palette/groove/recipe IDs, mapping curves/bounds, object motif ownership, transition graph, seed, uncertainties, review status, exact approved hash/version/reviewer. Plan is data, not arbitrary executable code. Edits/stale assets invalidate approval. |
| ClockMapping | Source/destination domains and epochs, anchors, offset/rate estimate, uncertainty and validity; reject stale conversions. |
| RunManifest / EvaluationReport | Exact commands, code/config/data/model/schema hashes, split membership, runtime, actual results/evidence paths, mode and passed/failed/not-run status. Targets are separate from measurements and release status. |

## Cross-contract obligations
Validate referential integrity, lane conflict resolution and allowed transitions locally even after schema validation. Repeated input+version+parameters+seed must resolve identical symbolic events; rendered determinism must state renderer/platform scope. Identify actual geometry algorithms and uncertainty; do not infer physical impulse from distance alone. Mark `real_device`, `replay`, `synthetic`, `cached_gpt`, `manual_plan`, `keyboard` as independent acquisition/planning provenance dimensions where appropriate, not a single ambiguous label.

## Executable entrypoints and bounds

`make test-contracts` checks canonical schema and all shared positive/negative fixtures in both languages. `validate` in src/scenescore/contracts.py and packages/contracts/validate.ts validates a single record; validate_bundle/validateBundle validates fixture references. EEGChunk explicitly names its device_epoch separately from host receipt epoch; sample/drop counts reconcile stream continuity. FakeScheduler requires mapped transport times passed separately and never assumes raw device seconds equal transport seconds.

Approval verification binds exact payload bytes plus scene/composition hashes; schema review_status alone is not execution approval. Provider projection, synthetic approval and audio-manifest fixtures are not actual model responses, human approvals or media. For domain-specific scientific, geometric and musical validations, consult EVALUATION and phase cards; no passing placeholder represents them.

Module mounting/adapter signatures: services/local/README.md. Generated declarations must match the canonical schema after `npm run generate`. Domain capability wrappers may need versioned contract amendments; workers must not silently expand the frozen schema.

## Phase 2 module supplements

Canonical 0.1/freeze remains unchanged. Geometry-rich summaries, parts/rests and arranger `Policy` are explicitly module-versioned supplements, never extra fields silently added to canonical records. Arranger hashes cover the entire supplied scene/state/event set and the composition plus exact groove; policy/compiler/brief hash binds the approved numeric rules. Source ordering is canonicalized where it affects output. A sparse compact motion summary can be adequate for planning but inadequate for causal conducting; unavailable coverage holds.

`TransitionPreview` is unapproved audition data. `ApprovedSession` additionally checks the exact payload bytes, approval decision and current input hashes. The future executor must still validate canonical ControlAction quality, expiry, approved-plan hash and clock mapping. Neither compiler starts audio or treats a provenance label as hardware verification. Candidate pitched renderer envelopes fit inside declared intervals, including their fades; catalogue renders use separately documented natural release tails.
