# Local service mounting contract

Entrypoint: `scenescore.service:app` under src/, served on loopback only. Phase 1 exposes GET /health, GET /capabilities, POST /contracts/validate, POST /capabilities/run, and a one-message synthetic WebSocket /ws/fixtures. It does not start capture, rendering, synthesis or network model calls.

Phase 2 workers export a FastAPI APIRouter as `router` from their owned module's `api.py`, and a synchronous `health() -> dict` reporting available/unavailable/unverified with reason. No import-time jobs or global app creation. The integrator alone mounts routers under `/muse`, `/scene`, `/music`, `/arranger`; the UI consumes versioned JSON contracts. Future streams send one canonical record per message, with explicit session/sequence/clock epoch. Error envelopes contain code, message and retryable boolean; real stream lifecycle is Phase 2A.

Capability functions take one validated record plus a scoped output Path and declared budget. Return a validated canonical output record plus RunManifest evidence. Every new executable adapter needs cancellation, bounded runtime, concurrency, path, cache and teardown tests before registration. Domain capability IDs currently report NOT_IMPLEMENTED. No subprocess shell strings, automatic agents or external plugins.

## Phase 2 wave mounting

Root now mounts all four documented routers. They provide diagnostics/queries/local bounded plan preview, with no import-time or HTTP-triggered capture, render or provider job. Health distinguishes optional external prerequisites. This is module conformance, not a Phase 3B real-time transport implementation. Future ControlAction execution must verify quality/expiry/hash and map clock epochs explicitly. Existing one-message synthetic WebSocket remains labelled synthetic.

The one-canonical-record dispatcher stays registered for contracts.validate only. `tools/capabilities.yaml.module_implementations` records module availability separately; a generic multi-record job/summary/plan envelope needs its own integrator contract/lifecycle review.

## Phase 3 studio

`make demo` prepares/builds existing verified assets and starts this same loopback service. A final fixed StaticFiles mount serves only `artifacts/web-dist`; module/API routes retain precedence. HTTP/WebSocket requests that supply an Origin must use the same localhost/127.0.0.1 origin and port. CLI clients without Origin remain supported. No private EEG directory is mounted. The browser owns deterministic audio; the server never turns an HTTP request into a human approval, capture or model call. Health now reports phase 3B software; reports/phase3/GATE.md separately records its unpassed formal gate.
