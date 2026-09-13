# Node 08 physics review — scoped numerical evidence

Date: 2026-09-13. Scope: read-only audit of the current primary repository and final `artifacts/blender/revamp/review/` candidates. No source, candidate, selection, approval or frozen evidence was changed. This worker is independent of scene generation, but previously authored the validator and calibration/contact helpers; this is not an independent-author review of those helpers or a complete integrated-delivery review.

**Verdict: retain four narrowly scoped numerical passes. The required hero and complete revamp remain blocked.** No new counterexample was found in the four actual candidates during this review. Their passing numerical status must not be promoted to animation/product completion, full contact coverage, perceptual acceptance or human approval.

## Actual candidate checks

Using the current primary `modules.blender.production.validation.validate_candidate`, all five numerical gates passed with no issues for the following exact production/state inputs. Rendered-temporal and perceptual gates remained `NOT_RUN` in these reports.

| Final review candidate | Defensible scope | Duration | Additional direct audit |
|---|---|---:|---|
| `03_passing_ascent` | Prescribed lift/carriage transforms, solids and fresh replay; no dynamic response claim | 6 s | All active bodies stationary throughout final 0.25 s; no short repeated-pose runs |
| `04_orbital_approach` | Prescribed kinetic sculpture transforms, solids and fresh replay | 6 s | All active bodies stationary throughout final 0.25 s; no short repeated-pose runs |
| `05_bouncing_staircase-32` | One unit-mass sphere against fixed OBBs under the named analytic model; candidate-specific convergence and replay | 8 s | Bouncer final linear/angular speed zero; no short repeated-pose runs |
| `09_breathing_crowd` | Prescribed supported sculpture transforms, solids and fresh replay | 6 s | Final linear speed zero; maximum angular finite-difference noise 0.000010116 rad/s; no short repeated-pose runs |

The direct end-window check used all 61 samples spanning the final 0.25 s and adjacent position/quaternion differences. The cadence check scanned the actual active objects for repeated full-pose runs of two through eight samples. These are numerical checks, not complete native-cadence visual perception.

For all four candidates, `evaluated_geometry.json` contains exactly the production collider IDs. Evaluated local vertex extents agree with declared sphere radii/box half-extents to at most **1.90735e-7 m**. This is a useful independent check on these particular mesh records, not proof that every Blender collision property is audited automatically.

The previous read-only certificate run on both original and final-review staircase data found eight eligible rebound onsets and one supported ramp release. The final-review release is at **1.145446080 s**, bracketed by ticks 274–275, with 1/240 s uncertainty and confirmation at 1.179166667 s. Independent pre-support/post-flight fits differ by 1.52e-7 m and 8.23e-6 m/s; post-flight acceleration residual is 0.01644 m/s². Twenty contact-discontinuity intervals and two additional support-departure transitions remain explicitly unverified. That limited coverage is appropriate; no missing event may be fabricated to complete a soundtrack.

## Blocking findings and acceptance boundaries

### Required hero remains blocked

`reports/blender-revamp/native-calibration-final.json` is **FAILED**. All 36 referenced control-artifact hashes were independently rechecked here and still match. At the final 50/100-substep comparison, the finer zero-restitution transfer has outgoing relative speed **0.163740383 m/s**, exceeding the frozen 0.1 m/s cap. Maximum trajectory difference is **0.032570362 m**, exceeding 0.005 m. The successful drop and coarser individual transfer do not override the failed finer response and convergence.

The final review hero uses native Bullet, 7-second matched contact/miss/no-launch variants, and explicit physical parameters including zero restitution, ball mass 4 kg and angular damping 0.98. It does not fall within either alternate-backend scope. A staircase or driven-scene selection can support an explicitly partial draft integration, but cannot substitute for the requested launcher/contact/miss hero or close the hero-first dependency gate. No hero acceptance was issued by this audit.

### Blender-scene production mutations remain unperformed

`artifacts/blender/revamp/mutations-complete/audit.json` reports eight detected mutations, but explicitly records **`blender_jobs_started: 0`** and copied-sidecar injection. Its status `COMPLETED` and `coverage_gaps: []` concern that sidecar experiment only. They must not be reported as completion of the requested actual Blender-scene mutation gate.

The detector results are useful: penetration, hovering, scale growth, lost release velocity, fabricated miss impact and duplicated low-rate motion produced new relevant geometry/motion issues. Disabled-floor and stale-cache mutations were **integrity-only** detections. They do not prove that a disabled collider in a newly simulated scene causes the expected physical rejection. All 75 recorded source-input hashes were independently rechecked here and match. The audit records temporary mutants removed and owned process groups absent; this review did not rerun those jobs.

Required delivery action: keep a distinct `NOT_RUN`/blocked entry for Blender-generated mutation coverage, or complete those bounded experiments without changing thresholds. This does not erase the four actual numerical observations above, but prevents a complete production-robustness claim.

## Remaining validator/evidence limits

1. **Generic motion cases are weaker than their gate name.** The three driven candidates only supply a static floor/hub case. The final staircase's explicit case also names a static step. Their relevant evidence comes from scoped backend calibration, full trajectory geometry/rest checks, fresh replay and the independent supplements—not from those static cases alone. The validator's final-rest and repeated-low-rate checks run only on `dynamic` objects. The direct driven checks performed in this audit passed for these exact files; future driven candidates should not inherit that observation without equivalent candidate-specific checks.
2. **Collider dimensions are asserted by metadata.** The core geometry validator uses dimensions in `production.json`; it does not itself derive Blender rigid-body collision shapes from the saved `.blend`. The mesh-extent check above closes the obvious dimensional mismatch question for these four records, but should not be described as a general collider-property attestation. Preserving evaluated geometry, source snapshots, saved assets and replay lineage remains necessary.
3. **Calibration scope is correctly disjoint but deliberately narrow.** Analytic calibration requires one sphere/fixed boxes, matching mechanics parameters and analytic source hash, actual isolated e=1/e=.55 controls, and the candidate's own 32→64 comparison. Driven calibration forbids dynamic actors and requires the known affine carriage control. Neither certifies native multi-body contact. The analytic model's supported rolling resistance and friction are declared mechanics; this audit did not independently reproduce an isolated friction/rolling experiment in Blender.
4. **Certificate success means an eligible subset.** Contact/release helpers never import analytic contact flags and recheck the full physical gate. Their bounded ballistic fits explicitly reject edge/simultaneous or insufficient-window cases, and mark `coverage.complete=false`. They certify neither tangential impulse nor calibrated launcher impulse. Keep those limitations and null/unknown records in downstream handoff data.
5. **Hash validity is not every production prerequisite.** Current replay evidence compares all reopened poses against exact state hashes and settings/candidate-bound calibration artifacts. This review checked those files through the validator; it did not start a fresh Blender rebake, examine every Blender property interactively, decode/render clips, verify AV presentation timing, or audit the complete staged bundle/browser path. Those remain their owners' separate evidence, not implications of a physics pass.

## Judgment separation

| Evidence category | This audit's result |
|---|---|
| Automated/source/numerical | Four scoped passes recomputed; current control and mutation-input hashes checked; native calibration remains failed |
| Model judgment from stills | Not performed by this physics audit; another model's still review is separate evidence |
| Continuous native-motion perception | Unverified here; stills, timestamp checks and successful render commands cannot close it |
| Human acceptance/audition | Not granted or inferred; preserve exact approval gates and `approval:null` |

## Captured identities

| Source | SHA-256 |
|---|---|
| `modules/blender/production/validation.py` | `0a952f538270864a385a0deaefe19c9f236c2286cc3799bdc91809205598876c` |
| `modules/blender/production/analytic.py` | `42435782690496391c08c3b24612042745154890a898f36d9bad359012049433` |
| `modules/blender/production/backend_calibration.py` | `b952cd2ec74055c64b3724bd34f5ec9f03134f02b0e95c743bae7fde8432cea5` |
| `modules/blender/production/contact_intervals.py` | `bf25a56a441fa2461cec37bd7a187990b3fd493246f324a5b56eef711b1dfa7e` |
| `reports/blender-revamp/native-calibration-final.json` | `9bdcaea171a5d8b0a77c346c868df46f4b0251158207ca98251c8ccb23709c59` |
| `artifacts/blender/revamp/mutations-complete/audit.json` | `94b608652330eabd973a0a52024347f0028ec86376541e434df3d81ef834c4e0` |

| Candidate | `production.json` SHA-256 | `physics_states.jsonl` SHA-256 |
|---|---|---|
| 03 | `675641f1e4add9e219dc874c056d89b1978dea5e979cf9150bd18f20f110692b` | `7ef5828ee17617b3a6bdd743a0dd76972a59136f6f57e62b161b38f60841eae1` |
| 04 | `499eca7bf93d58c216c56403857157ccd08a63e013b9333b42e5369642b70012` | `00d2d37f733867a0f9cffb086ffd7a16420cf536239a83a761eb1860c03cf15f` |
| 05 | `921d18fdf190ef17b0fa1c9f039a92bd4e12555b636719919ec5848b0cd9da80` | `56a805f56e89fd38d3095b60c206dce4b8cea3118456ce18b01e345f2b56bb74` |
| 09 | `7d42ec0c9608727600413678f22e4e636f758b8bc53f1a0cfc73d2bca2dc9ea9` | `f6a54070166f74cd0b22a4c16584dc6b1996928afa7b4cd78cd510a4d4cb2951` |

## Commands actually run and resource teardown

Primary-repository Python heredocs used `/Users/agent/Desktop/SceneScore/.venv/bin/python` to import the current `validate_candidate` and `angular_distance`, read the four final candidate files, recompute gate results, scan adjacent active poses/end windows, and compare evaluated mesh extents against metadata. Separate read-only Python commands recomputed the 36 native-control and 75 mutation-source SHA-256 values. Source files were read with `sed`, `rg` and a diff against the validator worktree. No Blender or rendering job was started and no new media was created.

The four-candidate review command ran in recorded session 52207 and exited 0. All other audit commands also exited 0. No owned persistent process remains. This document is the only write in this bounded audit.
