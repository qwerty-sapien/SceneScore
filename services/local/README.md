# Local service mounting contract

Entrypoint: `scenescore.service:app` under src/, served on loopback only. Phase 1 exposes GET /health, GET /capabilities, POST /contracts/validate, POST /capabilities/run, and a one-message synthetic WebSocket /ws/fixtures. It does not start capture, rendering, synthesis or network model calls.

Phase 2 workers export a FastAPI APIRouter as `router` from their owned module's `api.py`, and a synchronous `health() -> dict` reporting available/unavailable/unverified with reason. No import-time jobs or global app creation. The integrator alone mounts routers under `/muse`, `/scene`, `/music`, `/arranger`; the UI consumes versioned JSON contracts. Future streams send one canonical record per message, with explicit session/sequence/clock epoch. Error envelopes contain code, message and retryable boolean; real stream lifecycle is Phase 2A.

Capability functions take one validated record plus a scoped output Path and declared budget. Return a validated canonical output record plus RunManifest evidence. Every new executable adapter needs cancellation, bounded runtime, concurrency, path, cache and teardown tests before registration. Domain capability IDs currently report NOT_IMPLEMENTED. No subprocess shell strings, automatic agents or external plugins.
