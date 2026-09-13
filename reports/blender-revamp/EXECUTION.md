# Blender production DAG execution ledger

Input: `blender_revamp/scenescore_blender_revamp_patched/START_HERE.md`.
Base: `527f949`. The supplied pack's 30 indexed hashes match. Existing untracked
inputs and frozen review artifacts are preserved.

## Current checkpoint

00–03 implemented with separate worker worktrees and independent handoffs. Stages,
process cleanup, workshop recipes, solid geometry checks, roles and versioned
music handoff preserve canonical 0.1 and exact approval gates.

04/05 **BLOCKED for native hero**: native Bullet calibration failed after three
bounded repairs. Final 50→100-substep transfer differed 32.570mm (limit 5mm); outgoing
relative speed 0.163740 m/s (limit 0.1). A supported seven-second matched contact,
near-miss and launch-disabled set exists; it is not accepted. The separate fixed-
OBB/sphere staircase and prescribed lift/orbit/crowd have scoped numerical passes.

06 **PARTIAL**: all ten recipes and both extra hero controls have native 30 fps
neutral diagnostic movies (12 total), complete decoding and recoverable PNGs.
Four scoped passing candidates have 640×360 beauty previews. Missing ramp supports,
lift-post intersections and lift camera clipping were repaired in generation
source, rebaked/replayed and rerendered. No 1080p final hero/control was rendered
because its calibration prerequisite failed. Continuous-motion perception remains
UNVERIFIED; model still judgments do not close it.

07 **PARTIAL, explicit staged candidate**: exact staircase selection serves three
original-score excerpt bundles, music handoff and final draft mix/stem/mux sets.
All three final muxes decode 240 frames and 384,000 audio samples. Initial full browser
take P95 software drift 29.73 ms, seek/resume 26.13 ms, final repaired build 8.50 ms.
Physical AV latency, audio audition and human approval remain separate/unverified.
Original 304/244/280 score events survive; window projections 95/79/89 bound the 8 s
clip. Legacy six-bundle scene/music/plan data remain identical and no failed hero
became active. Music/Muse task changes are preserved.

08 **PARTIAL / remaining blockers explicit**: independent numerical, selection,
staging and runtime reviews performed; minimal repair findings closed. Eight
sidecar mutation checks and five actual Blender-scene faults were detected; the
latter used two baselines plus five mutants and 28 Blender jobs. Actual causal-
release, stale-cache and fabricated-miss scene mutations remain incomplete. A
browser download-handler packaging error invalidated earlier export copies;
three distinct exports were recreated in a fresh session and reaudited. Use only
`integration/final` and `final-exports`, not the superseded draft paths.

Authoritative final entry: [DELIVERY.md](DELIVERY.md); machine-readable catalogue,
final delivery audit, review addenda and teardown evidence are linked there.

Baseline `make test` passed: 257 Python, 65 contract TypeScript and 16 audio tests,
Ruff, typecheck and build. Log: `/private/tmp/scenescore-blender-revamp-baseline-tests.log`.
Independent references: 9 positives accepted / 9 negatives rejected. The original
hero's tower overlap was independently recomputed as 0.533744693 m at 20.28125 s.
This is a sidecar calculation, not a new inspection of the historical blend.

## Ownership

- Coordinator: shared configuration/contracts, this ledger, candidate selection,
  generation/export/presentation and directly affected integration.
- 01 tooling worker: `modules/blender/batch.py`, new process-helper tests and
  `docs/blender-revamp/TOOLING.md`; project MCP configuration belongs to coordinator.
- 02 creative worker: `docs/blender-revamp/BRIEF.md` only.
- 03 validation worker: `modules/blender/production/validation.py`,
  `modules/blender/tests/production/` and `docs/blender-revamp/ACCEPTANCE.md` only.
- Workers use separate worktrees. One owner per GUI session, blend, bake and
  candidate directory. Shared scope requests return to coordinator.

## Budget and gates

Local Blender only; two render threads; serial heavy jobs; 1,800 s/job;
14,400 cumulative Blender seconds and 20 GiB new artifacts. Three repair attempts
per failed gate. Preserve the best valid candidate and report persistent defects;
never relax an acceptance criterion after seeing a failure. Record PID/PGID,
command, runtime, exit and verified child-process teardown.

Keep integrity, physical, causal, visual, temporal and integration gates separate.
Every report binds exact input/config/source/bake/render identities. Rebuilds
invalidate affected downstream reports. Native-motion perception and human music
audition remain distinct from sampled model inspection.

## Production interchange v1

`production.json` records version `blender-production-1`, recipe/variant, seed,
physics_hz=240, render_fps=30, duration_s, gravity_m_s2, solver settings, source
fingerprint and `objects`. Each object has object_id, sonic_identity_id, role,
scored, mode (`dynamic`, `driven`, `passive`), shape (`sphere` or `box`),
radius_m or half_extents_m, and physical material/settings. All consequential
colliders are included; ornamental geometry is excluded.

`physics_states.jsonl` rows contain `tick`, `time_s`, and `objects` keyed by
object_id. Every object state contains position_m, quaternion_xyzw and scale.
Rows traverse integer simulation frames monotonically, including the audit right
endpoint. Positions/rotations come from the evaluated dependency graph. A fresh
process independently reopens the finalized playback blend and checks those
transforms. Render frames use f=1+tick/8 and cover [0,duration_s).

Generated source/cache and derived replay are separate, explicitly identified
artifacts. The human-visible scene and exports use the same finalized motion.


## Verified repair and resource evidence

Native failed calibration: `native-calibration-final.json`; analytic equation
review: `analytic-control-review.json`; mutation histories: `mutations/` and
`artifacts/blender/revamp/mutations-complete`. CLI stages record exact PID/PGID,
exit and group disappearance in candidate `jobs/*.job.json`. MCP production
inspection used pinned upstream protocol5/addon1.6 on loopback only. GUI PGID18425
was intentionally terminated after viewport capture; process group absence was
verified. Its -15 exit records teardown, not an inspection failure. No accepted
interactive edits were needed; camera/frame inspection was not saved.

Source capture now archives exact generation dependencies in each new candidate's
`generation_source/`; a bake refuses source changes after build. Render receipts
record their renderer hashes separately from simulation lineage. All diagnosis,
module fixtures and synthetic production evidence remain distinct from human
approval, hardware measurement and continuous-motion perception.
