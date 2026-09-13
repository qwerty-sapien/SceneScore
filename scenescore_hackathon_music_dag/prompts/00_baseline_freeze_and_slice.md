# 00 — verify the baseline and freeze the slice

**Owns:** `docs/decisions/`, `handoffs/`. Writes no implementation code beyond a throwaway
diagnostic. **Budget:** 25 minutes.

`REPO_BASELINE.md` states what this pack believes the repo contains. Your job is to
confirm or correct it, not to rediscover it from scratch.

## Verify, in this order

1. `make doctor` and `make test` actually pass on the current tree. Record the counts.
2. `modules/blender/geometry.py::pair_timeline` still emits the seven event types named in
   `examples/motion_event_taxonomy.json`, with the same field names.
3. `modules/arranger/core.py::LANES` still contains the five feature/lane pairs, and
   `motion_direction` still returns `0`, `+2` or `-2` with the deadband and lookback
   semantics described.
4. `packages/audio/transport.ts::Timeline.submit` still rejects on the exact reason strings
   listed in `INTERFACE_CONTRACT.md`. If a reason string has changed, the contract file
   changes with an integrator decision, not the code.
5. `packages/audio/model.ts::transition` still performs the dominant-prep split described
   in `REPO_BASELINE.md` fact 2.
6. `reports/phase3/GATE.md` is still the authoritative open-gate record, and the AV offset
   figure is still the one this pack plans around.

## Freeze and record

Write one decision record in `docs/decisions/` containing:

- **Scene:** one animation. Default `10_projectile_tower` (30 s, hero) unless node 00 finds
  it lacks a usable rebound episode, in which case name the substitute and say why.
  `02_near_miss_twins` is the mandatory near-miss check case regardless.
- **Music:** one composition and one groove for the demo path, plus at most one alternate
  for A/B. Record the source hash of each.
- **Write-scope confirmation:** the `write_scope` in `DAG.json` mapped onto files that
  actually exist. Any collision is resolved here, before 01 and 02 start in parallel.
- **Rebound feasibility:** whether the chosen scene contains at least one pair whose
  evaluated-area ratio exceeds 4.0 with a normal-velocity reversal. If not, 01 ships the
  descriptor plus a fixture but the demo claims nothing about rebound.
- **Acceptance checks** each downstream node will be measured against, and the time budget
  from `TIME_BUDGET.md` adjusted for what you found.

## Forbidden

Do not start EEG work. Do not change Blender physics or scene recipes. Do not implement a
new music stack. Do not modify `contracts/0.1/`, root locks or `.brief/`. Do not advance a
phase number; this pack is a vertical slice inside the authorized phase, not Phase 4.

## Done when

The decision record exists, names exact hashes, and a reader can tell which of the eight
motion semantics the chosen scene can actually demonstrate. Stop only for a real missing
prerequisite that blocks every vertical slice — not for an ambiguity you can decide and
record.
