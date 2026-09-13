# Node 08 physics review addendum — actual mutation evidence

Date: 2026-09-13. This addendum updates the earlier `physics-review.md` without
rewriting its historical evidence. Read-only scope: the completed
`artifacts/blender/revamp/blender-scene-mutations-1/` audit and the replacement
`artifacts/blender/revamp/review-camera-repair-2/03_passing_ascent/` candidate in the
primary repository. No source or candidate artifact was edited and no Blender job
was started by this review. This reviewer is independent of scene generation but
previously authored the validator and mutation wrapper; this is not an
independent-author audit of that implementation.

**Verdict: the five specified actual Blender faults are now demonstrated and
rejected. The replacement ascent candidate retains its scoped numerical pass.
The required hero and complete revamp remain blocked.** The earlier statement
that all Blender-scene mutations were unperformed is superseded for these five
experiments only. Native material calibration, causal launcher coverage,
continuous-motion perception and human approval do not pass by implication.

## Actual Blender mutation audit

The generated audit reports `PASSED`, with seven fresh scenes, **28 Blender child
jobs and seven independent Python validation jobs**. All 35 job records exactly
match the corresponding records embedded in `audit.json`; the Blender commands
use two threads and disabled auto-execution, with recorded limits at or below
1,800 seconds. Recorded cumulative Blender child duration is 27.972145585 s.
Every recorded process group was reported absent at teardown, and a fresh
read-only process-group existence check found all 35 absent during this review.
No process was signalled or terminated here.

Independently recomputed results:

| Experiment | Actual observed fault and evidence | Result |
| --- | --- | --- |
| Native e=0 drop baseline | Asset integrity, geometry, physical motion and fresh replay all pass; no issues | Baseline numerical pass; material calibration and overall physical candidate remain `NOT_RUN` |
| Prescribed carriage baseline | Same four applicable gates pass; no issues | Baseline numerical pass; no new calibration claim |
| Removed floor rigid body | Saved mutation evidence changes the actual floor rigid body to null; evaluated sphere/floor signed gap reaches **−0.395810673 m** at 0.6625 s, versus 0.003 m tolerance | `solid_penetration`; also `disabled_consequential_collider` |
| Initial penetration | Actual initial ball centre is z=0.100000001 m, radius 0.25 m; gap **−0.149999993 m** at tick 0, versus 0.003 m tolerance | `solid_penetration` |
| Kinematic hovering ball | Actual rigid-body `kinematic` becomes true while the intended participant remains dynamic; unsupported rest and **9.81 m/s²** free-flight acceleration error, versus 0.5 m/s² tolerance | `unsupported_rest` and `case_free_flight` |
| Animated uniform scale | Actual scale F-curves exist; evaluated scale drift **0.399999976**, versus 0.00001 tolerance | `rigid_scale_drift`; fresh replay also fails |
| Actual 30 Hz constant playback keys | Full comparison of **961** freshly reopened samples against the unchanged physics source yields **0.029166698 m** position error at tick 279 / 1.1625 s, versus 0.00001 m tolerance | `replay_evidence_mismatch`, independently confirmed from the actual state files |

All seven current `validate_candidate` results exactly match both their saved
`physical-validation.json` and the audit's embedded results. Each negative has a
new relevant error absent from its corresponding baseline. The disabled floor
therefore now has actual penetration evidence beyond a metadata-only rejection.
The scale experiment actually changes evaluated scale in this installed Blender;
it did not need invented or edited trajectory samples. The low-rate experiment
changes the saved playback animation, not the simulation sampling frequency.

A failed replay report currently causes the main validator to reject before
recomputing its pose maxima, leaving zeros in that report's
`independently_computed` field. Those zeros are not evidence that playback
matches. For the low-rate experiment, this addendum reran the wrapper's separate
complete, hash-bound actual-state comparison and confirmed the 29.167 mm error.
Scale-fault credit relies on independently measured physical scale drift, not on
that secondary replay report.

All **169** candidate artifact records were rehashed and their recorded file
sizes checked. All **98** referenced lineage entries also match; these reference
counts include files already counted among the 169 and are not additional unique
artifacts. Each candidate's nine captured generation-source files match its
production source map. The audit's current generation-source map, captured
validator source and mutator source all match their recorded hashes. There were
no hash, job-record or recomputed-validation discrepancies.

Job and log files are not included in the audit's per-candidate artifact map.
This review separately read all 35 job files, checked them structurally against
the embedded records, and calculated snapshot hashes of their contents and logs.
The aggregate fingerprints below use SHA-256 of UTF-8
`json.dumps(relative_path_to_sha256_map, sort_keys=True, separators=(',', ':'))`,
with paths relative to `blender-scene-mutations-1`.

| Evidence | SHA-256 |
| --- | --- |
| Completed `audit.json` | `0817c98874c02a5ca03aa0496fb894220732f2e02ea84675af784a86343dc860` |
| 35 job-file hash map | `78b6e73e753b7ec634f8dbb387cd262b26e9e22206fe920e112ec882ac10b076` |
| 35 log-file hash map | `e227d3db969680218a1817f1c0011cfbe038f1c2c88aaa8f9a15393c84d5d2ee` |
| Mutator source | `27314b489c32b4ed427ed9ec17175590e3c359740a3862d51637934155ca8050` |
| Independent validator source | `0a952f538270864a385a0deaefe19c9f236c2286cc3799bdc91809205598876c` |

## Replacement passing-ascent candidate

The candidate for current delivery is now
`review-camera-repair-2/03_passing_ascent`, replacing the earlier `review/03_passing_ascent`
entry for presentation. The captured generation source explicitly sets the
beauty lens to **44 mm**, compared with 48 mm in the earlier source. Its reported
camera transform is unchanged; this physics review did not visually judge the
new framing or inspect the lens interactively in Blender.

Current recomputation reports `physical_candidate: PASSED`, with asset,
geometry, physical motion, fresh replay and the appropriately scoped prescribed
mechanism calibration all passing. There are no issues. The saved numerical
report exactly matches recomputation. All **12** production lineage references,
**nine** captured source files and **18** candidate/control calibration artifact
references have matching hashes. The calibration's `candidate_inputs` names the
new production/state hashes, so this is not a status copied from the old camera
candidate.

The complete six-second trajectory comprises 1,441 samples at 240 Hz and is
byte-identical to the earlier ascent physics trajectory. The freshly reopened
playback sample file is also byte-identical to this physics source, yielding zero
position, orientation and scale mismatch over 14,410 object poses. The four
active mechanism bodies have zero measured linear and angular speed throughout
the final 0.25 s. Evaluated geometry covers exactly the ten declared collider IDs;
local mesh extents agree with declared collision dimensions to at most
1.90735e-7 m. Some evaluated triangle ordering/surface-area bytes differ from the
old geometry record; this review checked the new record directly.

This supports prescribed transform, geometry, supported ending and replay
claims for this exact candidate. It does not establish a dynamic lift response,
new native material calibration, a perceptual camera pass or a complete clip
review. Its numerical report still marks rendered-temporal and perceptual gates
`NOT_RUN`; any separate media verification belongs to its own evidence record.

| Replacement ascent evidence | SHA-256 |
| --- | --- |
| `production.json` | `33c2864d55be620b78043fe10a63c5fdd640dd16d24365cbe04d4338c8e8ae96` |
| `physics_states.jsonl` and `replay_states.jsonl` | `7ef5828ee17617b3a6bdd743a0dd76972a59136f6f57e62b161b38f60841eae1` |
| `simulation.blend` | `3681bcc0b88c1b71278531ba50d4cb88556221c8c85188c31f10b5be124661e2` |
| `scene.blend` | `38a82fc2f8fb24067a50ad9958bdbf76cdfd5e7033a251a1b4dccd59ca80b5fb` |
| `replay_validation.json` | `41306dae5153b3640fad28dec4e24b2d30d063196997eb1588323f5b496dc756` |
| `physical-validation.json` | `8bd865feb70ac2258b9ccbf7a1aefeb5c1ef2dae8015d649499b3b779b29ae53` |
| `solver_calibration.json` | `069381f53ad6c7a5843eb2143625cdd930f29055fbc22da8d3dc50848222fb8e` |

## Remaining blockers and judgment separation

Actual Blender-scene mutation coverage remains **NOT_RUN** for causal launcher
impulse/release-velocity loss and stale-cache reuse. The earlier sidecar
experiments demonstrate only their declared data mutations. A fabricated miss
impact was tested as a sidecar/event fault; no corresponding Blender-scene fault
was run or is inferred here. The new audit itself lists these residual limits.

The native zero-restitution calibration remains **FAILED**. Its report is
unchanged at SHA-256
`9bdcaea171a5d8b0a77c346c868df46f4b0251158207ca98251c8ccb23709c59`:
the final transfer and convergence failures described in the original review
still block the required native launcher/contact/miss hero. Passing negative
controls and an alternate prescribed or analytic candidate cannot replace that
hero gate. The other three previously reviewed alternate candidates are not
re-reviewed or newly promoted by this addendum.

| Judgment category | Result of this addendum |
| --- | --- |
| Automated numerical/source evidence | Five actual Blender faults detected; two limited baselines and replacement ascent recomputed; hashes and recorded process exits checked |
| Model visual judgment from stills | Not performed here |
| Complete continuous native-motion perception | Unverified; no pass inferred from renders, stills or numerical state samples |
| Integrated browser/audio/export review | Outside this physics addendum; coordinator's separate evidence required |
| Human approval/audition | Not granted or inferred; preserve exact gates and `approval:null` |

Read-only checks were run with the primary `.venv/bin/python` as Python heredocs:
current `validate_candidate` on all seven mutation cases and the replacement
ascent, `replay_position_difference` on the low-rate fault, SHA-256/size checks,
job-record comparisons, `os.killpg(pgid, 0)` existence checks, and direct
position/quaternion and mesh-extent calculations. The principal numerical audit
ran in session **57278** and exited 0; all supporting read commands exited 0.
This addendum is the sole write of this bounded review. No owned persistent
process remains.
