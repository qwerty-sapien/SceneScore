# Phase 2B integration request

Mount `modules.blender.api.router` under `/scene`; `health()` is read-only. No new dependencies or canonical-schema changes. `BLENDER_BIN` is optional for existing exported bundle queries. The supplied Blender image was mounted read-only for validation; it will be detached at teardown, so the temporary path is not a persistent installation.

Canonical `SceneManifest`, `ObjectState`, `InteractionEvent` remain contract 0.1. Rich evaluated static mesh features, event minima/end times, pair minima and substep/proxy limitations live in explicitly versioned module sidecars `geometry.json` (`blender-geometry-1`) and `summary.json` (`blender-summary-1`). `modules.blender.summary.compact_summary(Path)` returns the compact view. `event_query(Path,event_id)` and `state_query(Path,state_id)` return exact canonical records or raise `KeyError`. Full states remain local.

Do not register a generic render capability yet: use the explicit trusted-script serial CLI; capability cancellation/cache/budget semantics across service jobs require integrator design. CLI records PID/PGID, timeout, command and verified group disappearance. Rendering is independent of optional headset availability.

Exported contact is scripted analytic primitive/AABB geometry; physical impact remains false and impulse null. The primitive contact proxy and numeric tolerance do not certify a triangulated display-surface collision. Default hero source uses no rigid-body simulation. Box and sphere/box tunnelling remain bounded sampled checks rather than exact swept certification; sphere/sphere linear sweeps are exact. Do not promote these into measured force, output synchronization, audition or listening claims.
