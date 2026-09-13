# Muse double-blink to modulation DAG — revision 2

A repo-grounded prompt pack for the six-hour blink-to-control vertical. Start with
`BOOTSTRAP.txt`.

What changed from revision 1: the control seam is frozen in node 01 instead of being
described three different ways across the pack, which is what lets the later nodes run in
parallel; the detector nodes now name the modules, config defaults and gate values that
already exist in the repo rather than proposing a generic ladder; participant consent and
independent annotation are a protocol file rather than a clause; the latency ladder is a
checked artifact that proves the double-blink closure delay of 500 ms leaves 250 ms of
headroom under the repo's 750 ms gate; and the ownership collision where this pack and the
music pack both claimed the harmonic transition is resolved by a byte-identical
`INTERFACE_CONTRACT.md`.

- `REPO_BASELINE.md` — audited state of the live repo, to be re-verified in node 00.
- `INTERFACE_CONTRACT.md` — shared seam. Byte-identical in the music pack.
- `PARTICIPANT_PROTOCOL.md` — consent, labelling independence and data locality.
- `TIME_BUDGET.md` — the six-hour allocation and the honest reachable end states.
- `examples/` — the latency ladder, fourteen grammar control cases, and a runnable checker.
  `PACK_VALIDATION.json` records its actual output.
