# Additive music-vertical preparation CLI

Ready for coordinator integration. Owned files are only
`tools/prepare_music_vertical.py`, `tests/test_music_vertical_preparation.py`, and
this note. Existing preparation, demo, browser, audio-engine and transport files
were not changed. All node-02/node-03 files and media remain frozen.

CLI SHA-256: `a4dc87be0b43fb040f784f9ffa3095dbb2db3dc3efa2ff6a9832500b01c132f3`.
Test SHA-256: `8a8b1cc4d6aa58a42c2074c046c8df5b062fd25ddf04c45b0c2f0fb58178a4cd`.
Worktree: `/private/tmp/scenescore-music-source`.

## Exact coordinator command

After the reviewed node-01/02/03/04/05 APIs are integrated into the root, run from
`/Users/agent/Desktop/SceneScore`:

```sh
PYTHONPATH=.:src .venv/bin/python tools/prepare_music_vertical.py --repo-root /Users/agent/Desktop/SceneScore --out artifacts/music-vertical/candidate-v1
```

The defaults are the invoking script's repository root and the same relative output
directory. `--out` must name a new directory beneath `artifacts/music-vertical`;
existing output and symlinked destinations are refused. No alternate scene/groove
selection exists. The input is exactly
`artifacts/blender/validated-hero/10_projectile_tower-default`, with the eight input
hashes frozen by `reports/music-vertical/BASELINE.json`, 30 seconds, 8 fps, seed 42,
the authored-ending `build_vertical_score()` edition and exact light-swing groove.
The explicit manual motion focus is `10_projectile_tower:tower-2`.

Dependencies: current `Context.scene_inputs`, `compile_vertical_preview(ctx,
geometry=..., seed=42, mapping_config={'focus_object_id': ...})`, node-02 source,
node-03 transforms, node-01 motion semantics and transitions-v2 sidecar/table.
The motion compiler return contract was coordinated directly with its owner.

## Candidate files and consumer fields

Primary bundle: `candidate.json`; catalog: `catalog.json`; copied exact video:
`preview.mp4`; editable mapped MIDI: `score.mid` when supported. The catalog keeps
the existing entry shape `{id,title,variant,groove,url,sha256}`, with URL
`candidate.json`. This whole new directory can be copied to the separate public
music-vertical location without changing the legacy studio output.

Other files: `plan.json`, `scene-input.json`, `composition-input.json`,
`source-events.json`, `events.json`, `unmodified-events.json`, `source-score.json`,
`source-sidecar.json`, `control-track.json`, `control-track-input.json`, `holds.json`,
`mapping-binding.json`, `mapping-audit.json`, `mapping.json`, `input-hashes.json`,
`code-hashes.json`, `geometry.json`, `summary.json`, and
`preparation-manifest.json`. The manifest hashes every written candidate file.

The candidate contains `scene`, `composition`, `groove`, `states`, `interactions`,
mapped `events`, source-only `source_events`, fair-A/B `unmodified_events`, exact
`plan_bytes`, `scene_hash`, `composition_hash`, `video_sha256` and
`music_vertical` (transition version 2, declared safe ticks, jazz disabled).
`unmodified_events` is the unchanged source **plus the same Foley** used by the
mapped output; `source_events` preserves the bound catalogue music/brush stream
separately. Both `foley_events` and `comparison_policy` make the distinction explicit.

Exact byte strings are provided for scene inputs, composition inputs, source events,
mapped events and unmodified events; their hashes match the corresponding parsed
records. `events_bytes`/`events_sha256` always refer to mapped events.
`source_events_bytes`/`source_events_sha256` always refer to the source-only stream.
Do not recompute their hashes by JavaScript serialization: Python's retained `0.0`
and JavaScript's `0` may be structurally equal but have different bytes.

The final behavior binding includes:

- `mapping_binding_bytes`: exact encoded `mapping_provenance.binding`, matching its
  `binding_sha256`, which must also appear in `plan.provenance.input_hashes`.
- `control_track_input_bytes`: exact control track with only its top-level
  `provenance` removed, matching `binding.control_track_sha256`.
- `holds_bytes`: exact holds list, matching `binding.holds_sha256`.

These bytes and parsed-record matching allow the loader to reject control/hold edits
that retain old approval inputs. No canonical schema field was added.

All outputs carry `approval:null`, `AUDITION_PENDING`, `DRAFT_NOT_APPROVED`, source
`SYNTHETIC_TEST`, manual-plan provenance and
`animation_label: 'LEGACY SYNTHETIC ANIMATION · 8 fps'`. Browser and physical output
measurement flags are false. Preparation never claims an audition or actual runtime
control event, and never starts a browser or renderer.

## MIDI and bounds

The dedicated adapter reuses the existing `_track`/`_varlen` binary helpers without
changing the legacy renderer. It exports stable lane/object tracks, including all
harmony and object-motif lanes, using at most 15 pitched MIDI channels. Brushes use
percussion channel 10 (zero-based index 9); Foley remains in scene-time JSON.
The source is constant 96 BPM. Staccato/tenuto use the current browser's .45/.94
gate fractions; MIDI cannot reproduce synth envelopes or continuous brushes, so
canonical events and control JSON remain authoritative. Unsupported voice types,
tempo maps or excess pitched tracks yield an explicit MIDI `not_run` reason and
preserve the complete editable JSON instead of silently dropping voices.

Input bounds: at most 60 scene seconds (this fixed candidate is exactly 30), 5,000
events per prepared sequence, 30,000 states, 512 interactions, 64 MiB metadata,
128 MiB video and 96 MiB combined output. A 120-second preparation budget is checked
before output creation. Code and input hashes are rechecked after compilation.
Invalid plans, event references, stale input bytes, changed behavior hashes or
fabricated approval are rejected before output creation. Fresh output files use
exclusive creation; failed writes remove only files created by this invocation.

## Actual evidence and cleanup

Commands run in the isolated source worktree:

- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest -q tests/test_music_vertical_preparation.py`:
  **13 passed**, 23.78 seconds.
- `/Users/agent/Desktop/SceneScore/.venv/bin/ruff check tools/prepare_music_vertical.py tests/test_music_vertical_preparation.py`:
  **passed**.
- `git diff --check`: **passed**.
- CLI `--help`: **passed**, without importing the unfinished motion compiler.

Tests use explicitly labelled synthetic file bytes and a fixture compiler adapter.
They validate exact byte/hash and parsed-record agreement, stable output, fair Foley,
catalog hashes, complete harmony/object MIDI tracks, channel-budget refusal, stale
assets, output preservation, output scope, plan corruption, duration/event overflow,
invented approval, changed event hashes and stale mapping/control/hold bindings.
They do not claim the real hero was prepared or rendered by this worker.

Final test session 69598 exited **0**; prior completed fixture-check sessions 17546
and 89040 exited **0**. Ruff, help and diff commands completed. No server, browser,
container or persistent job was started. The actual root preparation and subsequent
48-kHz static render remain coordinator actions; this worker made no root write.
