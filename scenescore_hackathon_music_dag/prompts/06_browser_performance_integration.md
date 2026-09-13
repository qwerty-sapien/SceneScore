# 06 — integrate into the existing studio

**Owns:** `apps/web/`, `packages/audio/engine.ts`, `packages/audio/transport.ts`.
**Budget:** 50 minutes.

`apps/web/src/main.tsx` already has a mode selector, arm and conduct controls, exact plan
approval, draft and approved export and a diagnostics panel. `Timeline.submit` already
validates the seam. Mount the new behaviour into that surface. Do not build a parallel
product.

## Wire up

- The node 04 control track drives the performance against the **same authoritative clock**
  as the video. The engine's audio clock is the reference; video follows through the
  existing drift correction.
- The node 05 transition executes on an accepted `ControlAction` through the existing
  `Timeline.submit` path, with the acknowledgement scheduled before the boundary.
- Keyboard, synthetic replay and (when the Muse pack lands) live events reach the same
  entry point. `REAL_REPLAY` and `LIVE_MUSE` stay visibly disabled until that pack proves
  them; a disabled option that reads as available is a truthfulness defect.

## Show, minimally

Current key and chord, read from the actual engine state and never from an optimistic
animation. The active motion feature bucket. The accepted control, its acknowledgement,
the running progression and the boundary at which the key lands. Suppressed or rejected
actions with their enumerated reason. Keep the debug view collapsible so the pitch is not
a dashboard.

Preserve the existing approval semantics exactly: audition is available before approval,
performance is not; editing a plan clears approval; an automated identity must not be able
to click approve.

## Instrument

Record the `INTERFACE_CONTRACT.md` ladder stamps — `t2` through `t6` are yours — into the
export record alongside the existing `clock` block. Keep `physical_output_measured: false`
until someone actually measures it.

## Tests

Extend the existing Playwright and TypeScript suites: mode labelling is honest in all four
states; a simulated event produces an acknowledgement then a key change; rejection reasons
surface to the UI; pause clears pending controls; a second control inside a pending
request is refused with `one_pending_request_limit`; seek and restart do not orphan
scheduled events; a changed bundle or missing video fails visibly and recovers.

## Forbidden

A fast path that skips validation. UI work unrelated to explaining the interaction.
Displaying a replayed or simulated event as live. Claiming acoustic latency from scheduler
timestamps. Writing to `packages/audio/model.ts` — scoped request to node 05.

## Done when

`make demo` plays the animation with the reactive score, a keyboard control produces an
audible acknowledgement then a landing in the new key, all state shown matches the engine,
and the existing test suites still pass alongside the new ones.
