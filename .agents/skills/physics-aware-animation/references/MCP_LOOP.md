# MCP is an inspection/control interface, not a physics or taste model

Current upstream primary references checked 2026-09-13:
- https://github.com/ahujasid/blender-mcp
- https://github.com/ahujasid/blender-mcp/blob/main/src/blender_mcp/server.py
- https://docs.blender.org/UATEST/manual/en/dev/physics/rigid_body/world.html

Upstream exposes scene/object inspection, Python execution and viewport capture.
It is a third-party integration. Main may differ from this repo's pinned revision;
use the pinned server/addon protocol or explicitly test a new pair. Its current
code also illustrates why a text error can arrive without a tool-level error flag.

## Preflight

Verify the actual Blender executable/version/build, FFmpeg, project environment,
addon/server identities, protocol, loopback host/port and permissions. Generate
machine-local config from verified paths instead of copying the old absolute
`/Users/agent/...` command. Do not modify global config or enable extra asset APIs
just to make a smoke test pass. Keep the existing loopback restriction, safe mode
and telemetry opt-outs; verify the addon preference as well as server environment.
Do not start duplicate listeners. Use one owned GUI session for interactive MCP;
use independent background CLI jobs for bounded baking/rendering.

The upstream status error recorded by the repo is a real partial failure. Treat
capabilities separately: inspection may work while addon-status is broken. Never
turn this into an all-green smoke. The included patch returns nonzero when a
recognized tool/content failure occurred, while retaining all receipts.

## Working loop

1. Generate a scratch candidate from source and run cheap motion checks via CLI.
2. Open the candidate in the owned Blender GUI; call scene/object inspection.
3. Inspect camera, scale, collision proxies and evaluated transforms at selected
   frames; capture screenshots and an actual motion preview. Scrubbing an unbaked
   simulation out of order is not reproducibility evidence.
4. Name one observed failure and one falsifiable repair. Make a small scratch edit
   or change the source parameters. Do not bundle geometry, solver, timing, lights
   and camera changes into one unexplained action.
5. Inspect again. Transfer accepted edits into generator code and scene intent.
6. Rebuild to a new directory, invalidate affected evidence, replay in a fresh
   process and rerun numerical, temporal and full-motion/visual checks.
7. Record successful parameter changes as a tested example, not just a chat log.

Examples of specific repair hypotheses: the outgoing trajectory approaches the
post on the wrong side; the visible rail differs from the collider; the event is
hidden behind a support; the marble is too small on screen; a carrier produces
an unphysical velocity discontinuity. "Make it more realistic" is not a repair
hypothesis. A good screenshot is not evidence that the hypothesis passes over time.

Do not run long bakes inside a 30 s inspection call. Keep compute in bounded CLI
jobs with owned process groups and explicit timeouts. Save/exit only owned jobs.
Safe-mode rejection must be reported rather than worked around by disabling the
user's safeguards. This pack does not include a live MCP connection or installer.
