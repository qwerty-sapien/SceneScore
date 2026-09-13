# Node 04 — additive source-preserving music vertical

## Integration ownership and API

Append the region beginning `# Additive music vertical.` in this worktree's `modules/arranger/core.py` to the reviewed root core. Do not overwrite the root Context dependency. The worker's pre-04 prefix hashes to `1cea0b2eda18e8c3ccf240b43fa0d046dab759c490138f926fe7e1a44405f2f4`; no original function/import changed. The coordinator reported a further root-only `Context.scene_inputs` property while node 04 ran; preserve it. New helpers use the public `ctx.scene_hash`, so that additive property can remain.

```python
from modules.arranger.core import Context, Policy, compile_vertical_preview, validate_vertical_result
from modules.music.catalog import build_vertical_score

score = build_vertical_score()  # Frozen authored ending; legacy catalogue untouched.
ctx = Context(scene, full_states, canonical_interactions, score['composition'], score['groove'])
result = compile_vertical_preview(
    ctx, geometry=exact_geometry_json,
    mapping_config={'focus_object_id': '10_projectile_tower:tower-2'},
    policy=Policy(), seed=42, variation='base',
)
validate_vertical_result(result)  # Offline binding check; never approval.
```

`geometry` is required as a keyword argument. Other options are `policy`, `seed`, `variation`, `mapping_config`, and the existing default original-swing `brief`. The exact scene duration must equal the source score duration; no tempo, bar, cadence or video rescaling is invented here. The returned dictionary is fully JSON serializable.

Return fields:

- `plan`: canonical draft ArrangementPlan 0.1; explicit palette includes the original object-bell preset. All returned ScoreEvents use its ID. Fixed `motion_policy.focus_object_id` is set only from validated manual mapping config; the hero adapter passes tower-2. It yields −2 from the existing causal world-Z policy at scene time 18 s.
- `plan_payload`: exact canonical UTF-8 text; encode it for bytes. `plan_payload_sha256` binds those exact bytes. This is a draft, not an ApprovedSession.
- `source_events`: complete original catalogue-derived pitched/brush source, with authored ending supplied by node 02. `events`: mapped music plus Foley. `foley_events`: separate scene-second stream. `source_with_foley_events`: optional source A/B with identical Foley, so the comparison need not confuse Foley with music transformations.
- `control_track`: versioned time-indexed mapping intentions, using the existing bounded linear `curve` and mapping record shape. New feature/lane names stay outside canonical mappings/schema.
- `holds`, `audit`, `provenance`, `duration_s`, `approval:null`, `audition_status:AUDITION_PENDING`.

Control-track root: `document_type:SceneScoreMotionControlTrack`, `document_version:1`, `clock:scene`, `epoch:scene.id`, `duration_s`, `config`, `mappings`, `events`, `suppressed`, `provenance`. Each row has `id`, `source_event_id`, `feature`, `pair_id`, `object_ids`, `start_s`, `end_s`, `driver`, bounded `values` by lane, `intent`, `source_slot_ids`, `quantization_delay_s`. Instantaneous controls retain their exact start and use one source-frame display span. Selected source slots additionally expose per-slot `source_slot_delays_s`. Rebound rows include role IDs, area/retention, chain index and false physics disclaimers. Read active rows with half-open `start_s <= scene_time < end_s`.

Hold rows: `id`, `source_event_id`, `start_s`, `end_s`, `root_pc`, `withheld_pitch_classes`, `hold_beats`, `pair_id`, `reason:near_miss_withheld_resolution`, and explicit no-accent/no-Foley/no-key-change flags. Node 05/06 must keep its transition preparation out of these intervals or respect their withholding; consuming only mapped notes and ignoring a subsequently introduced harmonic transition would discard the hold policy. No runtime model call is required.

## Mapping behavior and explicit limits

Source material comes from `resolve_events`, including its single swing application. Only the three `soft_comp` voices in each authored accompaniment slot are normalized by pitch/ID to `harmony-0/1/2`; bass stays bass, lead stays `piano_or_lead`. This lets node 05 reach existing harmony without changing a single source pitch or onset. Existing object-motif slots rotate deterministically among persistent object IDs; melodies are not duplicated. All object IDs remain stable across transposition.

The mapping configuration defaults to articulation, dynamics and ornaments enabled; one-beat holds; a 0.75-second maximum source-slot selection delay; at most 5% changed source note identity/timing and 10% changed lead identity/timing. Unknown/invalid options fail. Config and exact geometry/score/control hashes bind the opt-in brief, canonical config hash, and additional plan input hash. Palette/focus extensions belong only to the opt-in plan; legacy baseline/compile_preview/TransitionPreview remain unchanged and are not the execution path for this plan.

Approach uses two evaluated pair samples at or before each existing source slot, within the declared source cadence. It does not use the canonical future-minimum scalar, gap or outcome to change the earlier prefix. Missing causal coverage leaves that source slot unchanged and records why. The common approach realization is an explicit legato performance request; the tension/register/ornament values remain separately represented intentions, not an unbounded note generator.

Near miss begins at `minimum_s`, never bracket onset, and requires node 01's complete positive-bracket/no-tunnelling certificate. The current chord's third is omitted inside a full beat after the minimum; short retained fragments below 25 ms are omitted. Source-slot splits/omissions are explicit exceptions to occupied-note duration preservation, counted against the identity budget; score/media duration remains unchanged. Retained intervals before the minimum are symbolically unchanged. A renderer may place its release fade before a shortened endpoint, so acoustic prefix identity for a crossing sustained note still needs testing; the frozen hero has no such crossing third at either minimum. A hold that cannot fit before media end fails rather than quietly shortening the beat. No extra near-miss percussion/Foley/key change is created. Existing brushes are byte-identical.

Contact/collision and rebound choose existing source slots at/after their exact control timestamp and disclose the delay. They do not invent new melodies at an arbitrary contact time. A missing source slot logs an unavailable realization. Rebound gives the smaller owner the grace/tenuto figure, scales its separate velocity control by retention and chain decay, and biases its separate register via the bounded area-ratio curve. The anchor receives at most one selected lower staccato source note and no grace. If exact retention scaling exceeds node 03's ±32 velocity-delta bound, decoration is suppressed with a reason rather than silently claiming the requested scale was realized. Human assessment of these quantized figures remains pending.

Node 03 typed TransformRequests execute style controls first and decorations second, so its existing-ornament guard does not discard the requested retention velocity. Concurrent contact/rebound arbitration gives the rebound its intended articulation. Transform audits expose applied/suppressed status. Added-event and simultaneous-ornament bounds remain 12/second and two; a final combined density check includes any hold-resume notes and excludes Foley. Source-note identity/timing remains >=95%, lead >=90%; failure raises instead of widening the budget. Dynamics and register changes are explicitly listed; velocity is unchanged except for declared rebound scaling. Accepted key changes remain a separate path and preserve these controls.

## Exact binding convention

`provenance.binding` contains semantic/config/version/seed hashes, control-track content hash, holds hash, source/mapped musical hashes and transform budgets. Musical hashes omit only `plan_id` and `provenance`, avoiding circular plan references. The control-track content hash omits only its final `provenance` field, which itself points to the exact plan payload. Exact full source/mapped record hashes are also returned. `validate_vertical_result` rejects changed notes, controls, holds or payloads. This validator never creates or upgrades approval.

Preparation, UI, live scheduling, render/mux output, transition integration and human approval are coordinator/node 05–08 ownership. The candidate is deterministic offline data and does not launch any job.
