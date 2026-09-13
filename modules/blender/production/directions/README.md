# Explicit mechanics → Blender animation studies

This package prepares the user-selected thirty-second directions 06, 08 and 18. It follows the successful staircase's **computed SI mechanics → 240 Hz sampled motion → independently reopened Blender scene → 30 fps replay → complete rendered movie** method. Its backends have their own narrow, tested mechanics scopes. They do not certify native Bullet or arbitrary rigid-body interactions.

`rolling.py` owns the rolling courses and the polished sliding bead. `puck.py` owns planar disc contacts and coupled hinged mechanisms. `driver.py` renders their supplied shapes and transforms. Physical trajectories are never retimed or authored by the renderer. Only declared springs/compliant facings and the visible free cable segment may change extent; rigid actor scales remain one. Electrical indicators, when present, visualize recorded physical crossings and contribute no force.

The CLI refuses existing candidate directories at preparation, records source snapshots, and rejects changed inputs before a downstream job. Any physical or visual generation change needs a new candidate. Earlier trials remain evidence. To reproduce older outputs after source changes, use their `generation_source/` files in an isolated checkout rather than replacing current project files.

Run from the SceneScore repository with its existing `.venv`; no additional dependencies are required. The verified Blender installation is `/Applications/Blender.app/Contents/MacOS/Blender`. Use normal host access for Blender: the first sandboxed fixture process crashed at startup, while the bounded host invocation succeeded. No global application or Codex setting is changed.

```sh
.venv/bin/python tools/direction_animations.py prepare --direction 18 --out artifacts/blender/revamp/directions/NEW-CANDIDATE
.venv/bin/python tools/direction_animations.py build --out artifacts/blender/revamp/directions/NEW-CANDIDATE
.venv/bin/python tools/direction_animations.py replay --out artifacts/blender/revamp/directions/NEW-CANDIDATE
.venv/bin/python tools/direction_animations.py verify --out artifacts/blender/revamp/directions/NEW-CANDIDATE
.venv/bin/python tools/direction_animations.py stills --out artifacts/blender/revamp/directions/NEW-CANDIDATE --width 1280
# Inspect framing, support and contact visibility before the full render.
.venv/bin/python tools/direction_animations.py render --out artifacts/blender/revamp/directions/NEW-CANDIDATE --width 1280 --timeout 1800
.venv/bin/python tools/direction_animations.py encode --out artifacts/blender/revamp/directions/NEW-CANDIDATE
.venv/bin/python tools/direction_animations.py media --out artifacts/blender/revamp/directions/NEW-CANDIDATE
```

The renderer is bounded to two threads; heavy jobs run serially under a task lock. Per-job timeouts are at most 1,800 seconds, cumulative new-study jobs at most four hours, with a 20 GiB output cap and a 3 GiB free-space prerequisite. Every subprocess group is recorded, stopped/reaped if needed, and checked absent. Successful processes alone do not establish physically correct motion. Backend controls, independent source review, dependency-graph replay, full frame/PTS/decode checks and visible media inspection are separate evidence.

Each completed candidate retains `packet.json`, `mechanics_states.jsonl`, source hashes/snapshots, `simulation.blend`, editable `scene.blend`, evaluated geometry, both reopened motion reports, recoverable PNG frames and `renders/video.mp4`. These are silent animation studies; no new music approval, deployment, or change to the historical scene selection is made.
