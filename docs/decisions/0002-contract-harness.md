# ADR 0002 — Phase 1 contract harness

Accepted for the authorized Phase 1, 2026-09-11. Contract version 0.1 is frozen at the phase completion commit and contracts-v0.1 tag. A shared semantic change requires integrator review, version decision, fixtures and generated-type updates.

Canonical source: contracts/0.1/schema.json (JSON Schema 2020-12, 18 top-level record kinds). Python jsonschema and TypeScript Ajv independently validate the same labelled fixture suite; local semantic functions check relationships schemas cannot express. TypeScript declarations are generated, never hand-maintained. Python representations are validated dictionaries at the boundary; no separate handwritten schema model is authoritative. validate_bundle/validateBundle provide fixture-level object/catalogue/plan reference checks. They do not prove physical geometry or music quality.

Use exact persisted UTF-8 payload bytes for approval/content SHA-256. Approval is a separate record, avoiding self-hashing. Do not deserialize/reserialize before verifying approval. Cache serialization is separately defined as compact sorted-key Python JSON for the sole Python validation adapter, keyed with full schema hash and adapter version; input carries seed/config provenance. Do not treat that encoding as an interoperable approval canonicalizer.

The Desktop shell resolves existing Python 3.13.7 at /usr/local/bin/python3; the initial workspace resolves a different existing Homebrew Python. Bind explicitly to the Desktop interpreter, create a local venv and lock it without runtime downloads. Node 24.14.0 and npm 11.9.0 remain unchanged. uv.lock and package-lock.json capture the actual resolved versions. No NumPy, Muse transport, ML model, Blender dependency or sound generator is installed by this phase. FastAPI plus an in-process synthetic WebSocket is a service skeleton; React/Vite shell is a scope/status page only.

A conservative provider projection is supplied, but model ID, API billing/access and supported subset remain unverified. No credentials/model pair is configured. Keep manual/fixture planning independent of cloud.

Only contracts.validate executes in the capability registry. All eleven domain capabilities report NOT_IMPLEMENTED. Their record-level input/output declarations are provisional adapter interfaces; compound/new domain request envelopes require an integrator contract amendment. Exact dispatch, zero external spend, finite budgets, scoped output/cache paths, concurrency and invalid-output rejection are tested. No unrestricted plugin loader or autonomous agents exist. FakeScheduler models boundary invariants only; production audio scheduling, expiry policy tuning and measured output remain Phase 2E.

Direct user refinements (optional Muse, mandatory keyboard/replay core, explicit jazz creative traits) are recorded in VISION and SS-030/031. No missing planning ZIP content is inferred.
