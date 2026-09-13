# SceneScore animation-to-music DAG — revision 2

A repo-grounded prompt pack for the six-hour animation-to-music vertical. Start with
`BOOTSTRAP.txt`.

What changed from revision 1: every prompt now names the file, contract and function it
owns instead of describing a generic music system; the harmonic transition is shipped as
a frozen 216-entry table rather than an instruction to invent one; the eight motion
semantics are specified with drivers, ranges and forbidden behaviours; the demo gate is
split into a measurement node and an independent review node because the repo's real
blocker is audition and AV timing, not missing code; and the seam with the Muse pack is a
single byte-identical `INTERFACE_CONTRACT.md` that resolves the ownership collision where
both packs previously claimed the harmonic transition.

- `REPO_BASELINE.md` — audited state of the live repo, to be re-verified in node 00.
- `INTERFACE_CONTRACT.md` — shared seam. Byte-identical in the Muse pack.
- `TIME_BUDGET.md` — the six-hour allocation and what is explicitly out of slice.
- `examples/` — the frozen transition table, the motion taxonomy, and a runnable checker
  with positive and negative controls. `PACK_VALIDATION.json` records its actual output.
