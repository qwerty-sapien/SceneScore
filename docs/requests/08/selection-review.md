# Node 08 bounded selection and source-entry review

Reviewed 2026-09-13. This is an independent, read-only review of candidate selection and directly affected entry points. It is not the complete native-cadence audiovisual review. No Blender job, media generation, listening, browser playback or human approval occurred in this review.

## Verified

- `modules/blender/tests/test_selection.py`: **53 passed**; Ruff **passed**. Synthetic files and report-shaped metadata test integrity boundaries; they are explicitly not Blender, video or measured-motion evidence.
- The actual `staged_bundle()` lookup of `artifacts/blender/revamp/review/staircase-selection.json` passed the current resolver's physical/media/lineage checks. Candidate: `artifacts/blender/revamp/review/05_bouncing_staircase-32`; scene ID `05_bouncing_staircase:default:c5ee061e06e8074c`; selection SHA-256 `5e51110a180eeaf7912cf4be11b8f5d0e469a0d25b0522d936d8e892bfc9886d`. Label: `Staged production review · acceptance pending`; `approval:null`.
- The actual default `selected_bundle()` lookup still resolves `artifacts/blender/validated-hero/10_projectile_tower-default`, labelled `Legacy · authored choreography`. Both lookup calls left the active/historical selection bytes unchanged. `artifacts/blender/revamp/accepted-candidate.json` remains absent; historical `artifacts/blender/phase2b-gate.json` SHA-256 remains `3970c30e16629ff54a19325dcfd9615c87072143b7b9a7c6dc52d1859ccd6a30`.
- Production and staged selectors share physical/media proof validation. Tests reject missing/contradictory required gates and checks, wrong versions/identities, stale input hashes, unsealed or changed roles/handoff/features, changed source/video/index, escaped paths and non-null staged approval. Tests preserve explicit legacy compatibility and confirm staged lookup does not change default selection.
- Preparation, selected API aliases, demo preparation, audition bundle creation and mux provenance all reach the selection resolver. Generic non-rendered legacy API queries retain their existing compatibility path.

## Repair requests

### P1 — staged review URL opens the legacy studio

**Observed:** `tools/demo.py:17` advertises `/?review=1` and lines 21–26 prepare `/blender-review/`. At review time, `apps/web/src/main.tsx:11–12` only recognizes `music=1`; all other URLs load `/studio/`. Lines 16 and 22 initialize the legacy contact ID and only select the first catalogue entry for music mode. **Effect:** the advertised staged review URL does not load the explicit staged candidate, so this entry cannot establish candidate-coherent browser review. **Correction:** add explicit staged review routing, choose a valid staged catalogue entry and present its actual recipe without forcing contact/miss IDs; verify loaded bundle/video hashes and approval-null state in the browser. Owner: coordinator/integration. This is a source-observed defect; no browser reproduction was claimed.

### P2 — a new review sample can mix selected and historical candidates

**Observed:** `tools/sample_media.py:20–25` resolves the supplied selection for scene videos, while lines 26–28 always use `evaluated-hero-audition/{baseline,transition}.wav` and `phase3/performance/scenescore-DRAFT.mp4`. **Effect:** a newly created sample can describe selected production scenes alongside previews from a historical candidate without validating their identity relationship. **Correction:** require matched preview provenance for the explicit selection, or clearly isolate the historical stratum and refuse to claim it is the current integrated delivery. Preserve the already frozen sample/protocol. Owner: coordinator/integration. No frozen sample was redrawn.

### P2 — failed staging leaves a changed bundle index

**Observed:** `modules/blender/production/staging.py:35` writes the expanded bundle index before final selector verification at line 48. On failure, lines 49–51 remove only the new selection file. The function also does not exclude a candidate already referenced by an active selection. **Effect:** a failed staging attempt can leave a previously valid candidate's index changed, invalidating an existing selection that binds the old index hash. **Correction:** verify prospective sealed bytes before publishing, or restore the original index on failure; explicitly protect already selected immutable candidate directories or stage a distinct copy. Add a failure-path regression with an existing selection hash. Owner: production staging/coordinator. Current staircase review uses a separate candidate; no observed active selection was altered.

## Limits and gate status

Selection integrity: **PASSED within the tested scope**. Actual staged candidate identity lookup: **PASSED**. Source-entry integration review: **FAILED / repairs requested above**. Full physical, causal, visual, temporal, auditory, browser and continuous-motion judgments: **NOT RUN in this review**. Human acceptance: **PENDING**. Selector acceptance of current proof reports is not independent recomputation of their contents or proof of perceptual quality.

Commands actually run:

```sh
cd /private/tmp/scenescore-revamp-brief
PYTHONPATH=/private/tmp/scenescore-revamp-brief:/private/tmp/scenescore-revamp-brief/src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest -q --tb=line modules/blender/tests/test_selection.py
/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/blender/tests/test_selection.py
```

The actual lookup was a finite Python invocation in the primary repository using `staged_bundle`, `selected_bundle`, `DEFAULT_SELECTION`, `LEGACY_SELECTION` and SHA-256 before/after reads. No persistent process was started. Owned handoff paths are this report and `modules/blender/tests/test_selection.py`; copied source snapshots used for worktree imports must not be integrated.
