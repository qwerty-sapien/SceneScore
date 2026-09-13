# Standalone blink-training frontend

Owned directory: `apps/training/` in `/private/tmp/scenescore-muse-surface`.
No edits to the root shell, music modules, root scripts/dependencies, training service,
model worker, or shared browser. Parent integrates these files and runs browser checks.

The page calls the exact integrator v1 training API at 127.0.0.1:8767. Startup and
session tokens remain in memory; #token is removed before React mounts. Global fetch
is explicitly bound, cookies are omitted, redirects refused and request bodies bounded.
No source discovery, source connection, recording, training, download or deletion occurs
without its corresponding user action. A supplied fragment token only authenticates the
local service. No external fonts, analytics, raw-data upload or extra dependencies.

Implemented source/processing consent and distinct local-recording consent; source mode
truth; real-only explicit metadata confirmation for recording (default false, reset on
source/model/epoch/channel changes, sent as metadata_confirmed with record/start); explicit synthetic rehearsal; participant/refit/whole-session role; bounded capture;
B down/up with ordered same-ID/class markers, ignored repeats/editable inputs, button
focus support, blur release and release-before-stop; guided two-second preparation,
two-second cue and two-second quiet interval. Cues and markers are independent of model
output. Double is the positive gesture; single/triple/natural/movement/keypress-only are
comparison classes. Triple music controls remain absent.

Stacked raw traces display at most 2048 points, with per-channel median centering for
DISPLAY ONLY, explicit offset/scale/units and gaps/nonfinite values breaking paths.
No disconnected synthetic trace. The original samples are never modified. Recording stop
loads the resulting local session automatically. Manual review has device-time start/end,
class, reviewer and reviewed/uncertain status, explicit trace reload around edited bounds
(clamped to recording bounds and ten seconds), with full review history retained by the
API. Two-second preceding coverage and non-overlap obligations are visible. Uncertain
reviews remain excluded. Raw session download, model download and exact-ID deletion
are explicit authenticated local requests. No detector score is represented as accuracy.

Model state distinguishes missing model, synthetic rehearsal and experimental real model.
Held-out reports are rendered from actual API values and described only as window results.
No model or review creates music authority. Parent sets VITE_STUDIO_URL on publication;
default links to the existing local studio at http://127.0.0.1:5173.

Focused validation performed:

- `node --import tsx --test apps/training/tests/*.test.ts`: **10 passed**. Covers token
  scrubbing, bound browser fetch, exact consent/marker/delete payloads and errors,
  request bounds, B repeat/editable/button-focus/blur/queue behavior, cue phases,
  source truth, empty traces, large-DC morphology display and raw preservation.
- `./node_modules/.bin/tsc --noEmit -p apps/training/tsconfig.json`: **passed**.
- `./node_modules/.bin/vite build apps/training --outDir dist`: **passed**; standalone
  Vite production build, no new dependencies. `dist/` is ignored and excluded from
  handoff manifests; parent builds its exact integrated/publication environment.

An initial scoped typecheck caught an overly narrow inferred UUID factory type in the
controller test injection; it was explicitly typed as () => string and rerun successfully.
No browser/server/capture process was launched by this subtask. All test/build commands
completed; no persistent job, timer or container remains. Parent owns desktop/mobile
visual checks, actual synthetic browser API flow, real-device availability and deployment.
No real data, human approval, trained-model accuracy or hardware validation is claimed.
