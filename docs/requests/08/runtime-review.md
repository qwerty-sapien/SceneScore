# Node 08 bounded runtime review

Reviewed 2026-09-13 against `artifacts/blender/revamp/pre-window-integration/{apps/web/src/main.tsx,packages/audio/model.ts,packages/audio/engine.ts,packages/audio/transport.ts}` and its `source-hashes.json`. Scope is the optional Blender playback window, input binding, legacy/music/Muse regression surface and human approval behavior. No shared source was edited. No browser, audio output, Blender render or real Muse measurement was performed by this reviewer.

## Findings closed after independent repair checks

### R1 / P1 — removing the optional window retains a bound playback policy and prior approval

**Initial observation (before repair):** `packages/audio/blender-inputs.ts:20–27` validated the window only when present and did not compare it with `playback_policy`. `packages/audio/model.ts:29–32` binds the policy into scene inputs. `packages/audio/engine.ts:28–33,93,117` and `packages/audio/transport.ts:37,43` activate fade, output length and transition restrictions from the optional window instead of that bound policy.

An in-memory check on the exact current staircase review bundle removed only `playback_window`, `playback_window_bytes` and `playback_window_sha256`, leaving its hashed policy unchanged. Both `verifyBundle()` and `verifyApproval()` accepted it. The approval was ephemeral, explicitly `SYNTHETIC_IN_MEMORY_REGRESSION_ONLY`, and never written to an artifact. The unchanged policy still declared duration 8 s and final fade 0.01 s.

**Effect:** runtime behavior can omit the required fade and window restrictions without invalidating the plan's input identity. **Correction:** require paired policy/window presence for production bundles and exact agreement on version/start/duration/fps/fade; reject a retained policy with a missing window and the inverse. Keep the no-policy/no-window legacy path valid. Add a regression that retains the earlier plan/input hashes. Owner: coordinator/audio input validation. Initial status: **FAILED**. **CLOSED / RECHECK PASSED:** current `blender-inputs.ts:20–24` requires policy/window paired presence and exact equality of version/start/duration/fps/fade. Four in-memory mutations of the exact staged bundle now reject while retaining the original plan hash: remove window → `Playback policy and window must be paired`; remove policy → the same rejection; remove both → `Scene bytes mismatch`; change policy fade → `Playback policy differs from window`. A prior synthetic approval remains valid only for the intact input in the normal verified load path. No real approval was created or written.

### R2 / P2 — automatic demo focus can select a silent support

**Initial observation (before repair):** `apps/web/src/main.tsx:47–48` chose the first vertically moving state without the scored-object filter used by the conducting-focus selector. `newEngine(true, next)` accepts this preview override after the initial bundle role check.

A synthetic, in-memory ordering fixture prepended a moving state belonging to a silent support; the exact current selection expression chose that support (`scored:false`). The actual staircase bundle was not changed and its actual first moving body is the scored bouncer.

**Effect:** a catalogue recipe with a driven lift/support moving first can conduct from a silent participant, contradicting role ownership. **Correction:** restrict automatic focus selection to `role_supplement.scored_object_ids` when present and retain the current focus when no eligible moving body exists. Preserve existing behavior when the supplement is absent. Owner: coordinator/web. Initial status: **source/fixture failure for catalogue integration**, not an observed staircase playback defect. **CLOSED / RECHECK PASSED:** current `main.tsx:47` restricts moving-state candidates to scored IDs when the role supplement exists. The exact two live source statements were extracted and TypeScript-transpiled in memory: a silent moving body first in state order is skipped; absence of eligible moving scored bodies preserves the existing focus; absence of a role supplement retains legacy selection behavior. All three checks passed without changing the bundle.

## Review repairs already observed in current source

During this review the coordinator restricted new window creation to non-legacy candidates (`apps/web/tools/prepare.py:84–87`), restored the existing 18 s synthetic cue for non-window paths (`main.tsx:55`) and gave unapproved window audition an explicit Muse panel status (`main.tsx:95`). This resolves the initial source-level legacy opt-in and cue-regression findings. These edits were inspected. All six coordinator-generated bundles under `artifacts/blender/revamp/legacy-preparation-regression/` were independently checked with `verifyBundle(bundle, exactVideoBytes)`: all passed, none contains a window, each has null playback policy and approval. Scene, composition, groove, states, interactions, complete events, exact plan bytes, plan hash, scene hash, composition hash and video hash all match their corresponding saved pre-window studio bundle. The existing music-vertical bundle and exact video also pass without a window. Browser regression remains coordinator-owned.

The earlier staged URL finding is also repaired in source: `review=1` loads `/blender-review/`, selects an actual catalogue entry and displays a staged-review recipe caption. This source review does not substitute for the coordinator's browser verification.

## Passed checks and semantics

- Initial scoped Node tests: **49 passed, 0 failed, 2 skipped**. Skips were opt-in actual-candidate checks, not successful actual playback tests. Existing tests cover music transition output, independent lanes, acknowledgement scheduling, stale/duplicate controls, pause/seek epochs, cancellation of cooperative preparation, and exact approval payload/input hashes.
- Repair suite: **14 passed, 0 failed, 0 skipped**, with `SCENESCORE_REVIEW_BUNDLE` set to the actual staged candidate. This includes the paired-policy regressions and exact staged-input validation.
- `verifyBundle()` accepted the exact current public legacy studio, frozen music-vertical and staged staircase JSON inputs. Results are input/schema/hash verification only. Legacy and music bundles had no window; staircase had a window and scored bouncer focus.
- The 30 fps window requires integer frame count and exactly 1,600 samples per frame at 48 kHz. Original event objects/durations survive projection; the omitted/truncated ledgers are checked against the source. Audio rendering skips starts at or beyond the right endpoint while preserving source envelopes. The renderer's master fade bus is separate from gain/mute automation and is shared by mix/stems. The fade endpoint is rescheduled on resume.
- The new RVFC path maps media PTS to the audio scene anchor at `expectedDisplayTime`, recording callback and audio-context times separately. This is software timing; it does not measure display/acoustic output latency. Assessment of the 50 ms criterion belongs to the coordinator's measured trace with its declared percentile/coverage. No timing pass is inferred from this source analysis.
- Existing `approve()`/`verifyApproval()` implementations and gesture dispatch are unchanged from the snapshot. Loading/editing a plan clears approval, performance requires exact approval, and draft export carries `approval:null`. R1 is closed by the repaired input verifier; human approval and physical/auditory acceptance remain separate.

## Commands and cleanup

Repair check (actually run):

```sh
SCENESCORE_REVIEW_BUNDLE=apps/web/public/blender-review/05_bouncing_staircase-brush_swing_light_v1.json node --import tsx --test packages/audio/tests/window.test.ts packages/audio/tests/blender-inputs.test.ts
```

Initial broader regression command (actually run):

```sh
node --import tsx --test packages/audio/tests/window.test.ts packages/audio/tests/blender-inputs.test.ts packages/audio/tests/transport.test.ts packages/audio/tests/music-bundle.test.ts packages/audio/tests/music-runtime.test.ts packages/audio/tests/muse-control.test.ts packages/audio/tests/muse-preparation.test.ts
```

Also ran finite `node --import tsx --input-type=module` here-doc invocations for the initial three actual `verifyBundle()` calls, the initial R1/R2 reproductions, the six regenerated legacy bundle/video validations and eleven-field baseline comparisons, the exact music bundle/video validation, four repaired R1 mutations, and three repaired R2 cases using the extracted live source expressions. The legacy catalogue had exactly six entries and every comparison produced `changed_baseline_fields:[]`. None wrote source, media or approval artifacts. All owned command sessions exited with code 0; no persistent job was started.

Final bounded verdict: **R1 and R2 CLOSED; no new issue found in this recheck.** This bounded source review is not a product-completion, continuous-motion, auditory, physical-output or human-acceptance verdict. Only owned handoff: `docs/requests/08/runtime-review.md`.
