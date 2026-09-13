# Repo-specific findings — 13 September 2026

Scope: `SceneScore-main(1).zip`, two user-supplied `.mov` recordings and the supplied
search kit. Archive text was not indexed by Files search; the automatically mounted
archives were inspected directly. Sources were extracted below a separate audit
directory; no user repository was overwritten. Eleven very large generated event
JSON files were left compressed because this audit concerns generation/validation,
not their full musical event payloads. The archive has no `artifacts/` directory,
so historical `.blend`, calibration traces and caches referenced by reports were
not available for fresh replay. See pack `evidence/SOURCE_EXCERPTS.md` for literal
source snapshots and hashes, and `evidence/reference_metadata.json` for probes.

## Preserve the good infrastructure

The repo already has separate production build/bake/replay/verify/validate/export/
render stages, evaluated geometry, backend calibration, provenance hashes,
contact certificates, a music handoff, staged selection and MCP tooling. It is
incorrect to diagnose it as merely lacking rigid-body support or MCP.

I ran four existing host-side test files using Python 3.13.5:

```sh
PYTHONPATH=.:src python -m pytest \
  modules/blender/tests/test_analytic_sphere.py \
  modules/blender/tests/test_geometry.py \
  modules/blender/tests/production/test_validation.py \
  modules/blender/tests/production/test_backend_calibration.py -q
```

Result: **101 passed in 21.08 s**. These tests do not recreate the missing production
artifacts or establish render quality. There is no Blender executable in this
execution environment, and plugin discovery did not expose a live Blender tool.
No fresh Blender run, live MCP session, new render or human audition was performed.

## Concrete diagnosis

1. **The existing skill is mainly an exporter/auditor.**
   `.agents/skills/blender-scene-export/SKILL.md` focuses on evaluated sidecars,
   geometric QA and production gates. It does not give a reusable procedure for
   turning exemplar qualities into route geometry, physical parameter search,
   sparse choreography and a measured visual-improvement loop.

2. **Generation still assembles small hard-coded recipes.**
   `modules/blender/production/scenes.py:12-15` restricts recognized recipes.
   The staircase at lines 250-260 is four fixed steps, a ramp and a sphere. Lines
   329-345 use largely shared camera/light arrangements. This is a useful control
   scene but not comparable mechanical complexity or cinematic staging to the
   supplied layered-track references. The inspected source contains no import
   or runtime use of the exemplar search kit in its production scene builder.

3. **Physics progress is real but narrowly scoped.**
   `reports/blender-revamp/DELIVERY.md:29-32` reports failed native calibration:
   32.570 mm coarse/fine trajectory difference versus 5 mm allowed, and outgoing
   relative speed 0.163740 m/s versus 0.1 allowed. These are historical report
   values, not measurements made in this audit. The positively scoped staircase
   uses one sphere against fixed oriented boxes; other passes include prescribed
   supported mechanisms. These do not validate arbitrary multi-body scenes.

4. **The restitution issue already received investigation.**
   `docs/blender-revamp/RESTITUTION-DIAGNOSTIC.md` reports evidence consistent with
   positive-gap contact response and no verified configuration-only repair.
   Blindly increasing substeps is not a substantiated remedy for this snapshot.
   This does not establish that all Blender/Bullet versions or all scenarios have
   the same issue. Reproduce on the chosen runtime and isolate a new hypothesis.

5. **Quality gates have the right caveats but do not yet enforce an authoring loop.**
   `validation.py:424-426,520-523` leaves rendered/perceptual fields separate from
   overall physical PASSED. `DELIVERY.md:40` says full native-motion perception is
   unverified. Preserve these honest scopes; add a separate publication/story gate
   rather than renaming physical PASSED as visual acceptance.

6. **The bundled public preview is modest, and its endpoint is weak.**
   `apps/web/public/blender-review/05_bouncing_staircase.mp4` is an 8 s, 640×360
   staged clip. Sampled frames show one ball descending steps, traversing the
   otherwise mostly empty floor, then remaining near the frame's right boundary.
   That is an observed staging issue, not evidence of a particular solver error.
   It lacks the references' layered routing, mechanism variety and visual finish.

7. **MCP is present, with two immediately actionable reliability problems.**
   `.codex/config.toml` points to `/Users/agent/Desktop/SceneScore/...`; this is not
   portable to an arbitrary checkout. `tools/blender_mcp/client.py` stores tool
   replies and returns zero after the sequence regardless of `isError` or text
   errors. The historical `MCP.md` explicitly records `get_addon_status` returning
   a missing-module error while `isError` is false. The included optional patch
   fixes this client's reporting, not the upstream missing module. Re-pin/retest
   the server/addon pair only under an explicit compatibility change.

8. **Other runtime paths also need preflight.**
   The production CLI defaults to a macOS Blender path; `driver.py:246` hard-codes
   `/opt/homebrew/bin/ffmpeg`. Resolve/verify `BLENDER_BIN`, FFmpeg and the MCP
   environment per machine. Do not assume the uploaded ZIP transports those
   executables or the missing `artifacts/tools` environment.

9. **The current staged soundtrack is not the finished adaptive product.**
   `DELIVERY.md:19` labels current outputs as existing-score excerpts with adaptive
   scoring pending. Repairing the visual subsystem should preserve its exact
   scene-to-music handoff and editable stems, without claiming a new score adapter
   was implemented merely because a better video was muxed with old music.

## Highest-leverage sequence

First restore portable execution and truthful MCP status. Then produce one
original, visually stronger scene inside the tested one-sphere/fixed-obstacle
scope, using new candidate controls and full-motion review. In parallel, pursue a
separately bounded native multi-body calibration repair. Expand mechanism coverage
only after the first success is captured as a tested implementation exemplar.
Do not replace the whole repository, lower frozen tolerances, or build ten more
unreviewed recipes before one meets the visual target.
