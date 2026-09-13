# Audited baseline — what already exists

Audited against the working tree on 2026-09-12. These are prior facts to **re-verify in
node 00**, not facts to trust blindly. The tree moves; `reports/phase3/GATE.md` and
`docs/STATUS.md` are authoritative if they disagree with this file.

## Do not rebuild these

| Concern | Where it lives | State |
|---|---|---|
| Frozen schema 0.1 | `contracts/0.1/schema.json`, `packages/contracts/generated.d.ts` | Frozen. Amend only via scoped request. |
| Motion geometry | `modules/blender/geometry.py::pair_timeline` | Emits 7 event types with swept-sphere and tunnelling certification. |
| Ten scene recipes | `modules/blender/scenes/01..10` | Hero default `10_projectile_tower`, 30 s. `02_near_miss_twins` is the non-impact variant. |
| Original compositions | `modules/music/catalog.py` + `.brief/seeds/` | `tilted_blue_v1` 96 BPM, `almost_then_away_v1`, `corner_pocket_rag_v1`, `velvet_orbit_v1`. All unauditioned seeds. |
| Brush grooves | `.brief/seeds/brush_catalog.json` | `brush_swing_light_v1`, `brush_ballad_sparse_v1`, `brush_straight_rag_v1`. Unpitched, never transposed. |
| Symbolic event resolution | `modules/music/events.py` | Tick-to-second, swing applied exactly once, register-bounded transposition. |
| Arrangement compiler | `modules/arranger/core.py` | `Policy`, `Context`, `LANES`, `curve`, `motion_direction`, `Hysteresis`, `TransitionPreview`, `ApprovedSession`. |
| Browser audio | `packages/audio/{engine,transport,clock,model}.ts` | `Timeline.submit` validation, `Engine` scheduling, `transition()`, `keyboardAction`, `approve`/`verifyApproval`. |
| Studio UI | `apps/web/src/main.tsx` | Mode selector, arm/conduct, exact approval, draft and approved export, diagnostics. |

## The five facts that shape this pack

1. **`LANES` already maps five of the eight motion semantics.** `modules/arranger/core.py`
   defines `(approach, ornament)`, `(separation, dynamics)`, `(surface_gap, phrasing)`,
   `(collision, timbre)`, `(vertical_motion, register)`. Node 04 extends this table; it
   does not invent a mapping language.
2. **`transition()` in `packages/audio/model.ts` already does dominant-prep.** It splits a
   sounding note at the boundary, moves bass and `harmony-*` lanes to `(to+7)%12` before
   arrival and to the target after. That is `dominant_prep_v1` in the shipped table. Node
   05 generalizes it; it does not start from nothing.
3. **The signed interval comes from geometry, not from the gesture.** `motion_direction`
   and `model.ts::direction` compute a causal world-Z average over `lookback_s` with
   `deadband_m_s`; unknown coverage holds and yields a logged no-op.
4. **The real blocker is not code.** `reports/phase3/GATE.md` records 257 Python tests, 65
   TypeScript tests, a 30-second 308-event draft render, 48 kHz stereo plus four stems
   summing within 2 PCM LSB, and a verified MP4 mux — alongside an unanswered human
   approval request, `AUDITION_PENDING`, and a last-200-frame AV offset of **p95 137.33 ms
   against a proposed 50 ms target** on an 8 fps source.
5. **One known content defect is open.** The sparse `velvet_orbit_v1` lead sheet
   incorrectly calls it straight rag (`reports/media-evaluation/REVIEW.md`). Frozen source
   artifacts were preserved; the fix is a versioned correction, not an edit in place.

## Missing, and therefore this pack's actual work

- No `asymmetric_rebound` descriptor. Nothing in the repo expresses "a small object bounces
  off a larger one" as a musical event.
- `near_miss` is emitted by geometry but has no distinct musical treatment; it currently
  reads like a weak approach.
- The transition graph in `baseline()` is a bare 24-edge `from_pc/to_pc/±2` list with no
  voicings, no lead-in, no gesture identity and no acknowledgement.
- No acknowledgement gesture exists at all, so nothing is audible between the accepted
  control and the next bar boundary.
- No measured interval separates control acceptance from scheduled audible onset.

## Commands

`make install`, `make doctor`, `make test` (contracts, 257 pytest, ruff, TS tests,
typecheck, vite build), `make demo` (serves 127.0.0.1:8765). Node 24.x, npm 11.x, uv.
