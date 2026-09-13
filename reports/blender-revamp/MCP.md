# Actual project-scoped MCP smoke

Pinned upstream revision: `5f8ddaf6e987c4aa0c3467fcc548838b28f64477`.
Addon SHA-256: `f43469c8518c7021e0060e32cfe52e3beb126b0f62fbae7293106642a3ebda89`.
Server 1.9.1, addon 1.6, protocol 5; handshake observed in real MCP STDIO logs.
The addon is loaded only in an owned GUI session by the checked-in bootstrap;
it is not installed into the user's global Blender addon directory. Preferences
are not saved. Project server dependencies are frozen alongside the client.

Actual second smoke: get_scene_info, create cube via execute_blender_code,
get_object_info, delete cube, get_scene_info and get_viewport_screenshot completed.
Initial/final scene each had the same three factory objects. The inspected cube
was 0.1 m at (0,0,3), then absent. Actual screenshot inspected by coordinator.
Evidence: `artifacts/blender/revamp/mcp/smoke-2/calls.json` and PNG alongside it.

Separate upstream limitation: get_addon_status returned an error string,
`No module named blender_mcp.config`, while its MCP isError flag was false.
Its protocol handshake succeeded; the higher-level status call did not pass.
The pinned source's telemetry constructor imports that missing module. The task
does not patch upstream telemetry to manufacture a clean status. Server opt-out
environment flags are set; addon telemetry preference is explicitly false and
asserted before the final loopback listener starts. Asset integrations are off.

First attempt failed because client filename inspect.py shadowed Python's inspect
module and upstream auto-start occupied the owned socket. The client was renamed
and the bootstrap stops the upstream-owned auto-start listener before starting
the explicit 127.0.0.1 listener. Original failed job evidence is retained.

This smoke is tooling evidence, not production animation or perceptual approval.

## Final staged-candidate inspection

`artifacts/blender/revamp/mcp/final-inspection/client/calls.json` records actual
get_scene_info, read-only object/frame inspection and viewport capture for the
final staircase blend. The viewport PNG was inspected. No interactive scene
change was accepted or saved; final scene.blend SHA remains
854e00a2410ceab0aab690207a4649ad9c66c1255f7567cd954988ede1c6a30d.
Owned GUI PGID46186 was intentionally stopped after inspection; final process-table
audit confirms all recorded job groups absent. The upstream addon-status import
error remains; inspection/screenshot success does not turn it into a passing call.
