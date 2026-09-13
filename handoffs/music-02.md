# Music node 02 handoff

Machine gate **GO**; human audition **HUMAN-DECISION / AUDITION_PENDING**; approval
**null**. This releases nodes 03 and 05 for software/draft work. It does not approve
performance. Worktree `/private/tmp/scenescore-music-source`, base
`527f949fbf10319b84428b1cf510c5d2c1c205d2`; no commit/merge or root write performed.

Owned changes: `modules/music/catalog.py`, `modules/music/AUDITION.md`,
`modules/music/tests/test_vertical_source.py`, new
`modules/music/fixtures/music-vertical-source-v1.json`, and reproducible renderer
`modules/music/fixtures/render_vertical_source_v1.py`. No frozen fixture, schema,
dependency, renderer or catalogue version changed.

## Integration API

`modules.music.catalog.build_vertical_score()` returns a normal versioned score
supplement plus canonical `composition` and `groove`, and module metadata in `sidecar`.
Defaults are the frozen Tilted Blue/version 1, exact light-swing groove/version 1 and
30 seconds. Unknown IDs/versions, changed frozen hashes and a mismatched scene duration
fail explicitly. The ordinary `get_composition()` / `build_score()` paths stay unchanged.

`eligible_arrival_boundaries(composition)` validates complete bars and converts across
the tempo map. Sidecar keys: `eligible_arrival_ticks`, `eligible_arrival_seconds`,
`ending_region`, `source_hashes`, `composition_sha256`, `groove_sha256`, `terminal_s`,
`terminal_is_eligible` and `maximum_gap_including_edges_s`. Arrivals are internal bar
starts 2.5–27.5 seconds every 2.5 seconds (ticks 3840–42240 every 3840); no pitched
source event straddles them. The 30-second endpoint is ineligible. Maximum edge-inclusive
gap is 2.5 seconds against the four-second bound. Approval is still required.

Ending: final bar retains its two half-bar chord slots, now C7 / C6/9, and resolves
E4–D4–C4. Only two of 48 lead pitches change; 95.833% of lead notes are byte-identical,
100% of note onset/duration/velocity/articulation/swing flags are retained. Tempo
96 → 96 BPM; duration and bar topology unchanged. No listening quality is asserted.

Exact hashes: frozen composition
`9a517e3ff24dc2d2855168a8233b8477b9fa3a993d1d16724989667d289c947d`,
groove `4d537af9f3f293efecda5e07ed41e78a9f75d7787c152fbdeb47edf8c46b495d`,
authored composition `76d75e3e98d31c48c7ea234c987efc03972b8f11e616c187d74f0a10fc6bc530`.

## Actual checks and renders

- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest -q modules/music/tests`:
  **52 passed**, 33.38 seconds, two existing dependency deprecation warnings.
- Focused `... -m pytest -q modules/music/tests/test_vertical_source.py`: **4 passed**,
  4.25 seconds after the last added no-crossing-note boundary check. Initial four
  failures exposed half-bar harmony overlap; repaired by retaining original slots.
- `/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/music/catalog.py modules/music/tests/test_vertical_source.py modules/music/fixtures/render_vertical_source_v1.py`:
  **passed**.
- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python modules/music/fixtures/render_vertical_source_v1.py`:
  **two actual renders passed**, 8.33 and 8.58 seconds. The coordinator authorized the
  second render to supply both unchanged-source and authored-candidate evidence.

Exact output root: `/private/tmp/scenescore-music-source/artifacts/music/music-vertical-source/`.
`unmodified/mix.wav`: SHA
`9d3ccd60fad79f117b39d16275e30218309756809ee61ef90cd9d6b85c67af82`, RMS
0.019274696298396794. `authored-ending/mix.wav`: SHA
`ad365a0a4ad0732370551968c30782736500ccc36fa2f956270fd33e12cbe046`, RMS
0.019272529787528907. Both: 48 kHz mono PCM16, exactly 30 seconds / 1,440,000 frames,
peak 0.124176025390625, zero clipped samples, zero endpoints, four aligned stems.
Existing `stdlib-procedural-1` synthesis and envelopes were reused unchanged. Every
post-form sample in each stem was zero before dropping only the allocated 350-ms
empty tail. Manifests bind exact source code/score/event hashes, measures and commands.

The node's source files and render manifests preserve exact catalogue provenance;
the rendered composition seed is explicit in composition JSON and the groove keeps
seed 13007 independently. Vertical authored-edition provenance uses seed 42.

## Open human subgate and cleanup

No listening verdict, reviewer or review date exists. Cadence perception, balance,
click perception, timbral realism and synchronized reactions remain unheard. Velvet
Orbit's incorrect straight-rag lead-sheet sentence is deferred as a new-version repair,
since it is outside this slice; frozen evidence is preserved.

Render PID 29156 / exec session 46392 exited **0**. Test session 33933 exited **0**;
the final focused checks exited **0**. A direct `ps` inspection was sandbox-denied,
so it is not claimed as successful evidence; the execution tool confirmed actual
process completion. No server, browser, child worker, container or persistent job was
started. All node-02 commands completed and no node-02 job remains live.
