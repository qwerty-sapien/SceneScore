# Phase 4: independent release audit and five-hour demo rehearsal

Read AGENTS, VISION, EVALUATION, RUNBOOK, STATUS and all handoffs. Act as the release engineer. First assess the existing product; do not expand it. Own final cross-module fixes, evidence and the demo runbook. Preserve a reproducible baseline and revert risky last-minute changes.

## Evidence audit
For each MUST requirement inspect the implementation and an actual evidence artifact. Distinguish tests run from tests merely written. Verify real/synthetic/replay/device provenance, model/data/split hashes, source/scene/video alignment and arrangement approval. Check the RAGTM reuse claims against actual inspected code or label them unavailable.

Inspect the fitted blink artifact and report: real session counts, independent refits, intentional gestures, true/missed/duplicate commands, natural-activity exposure, false activations, availability, latency, thresholds and confidence bounds. Do not re-tune the final test. A small perfect test remains a small test. No claim of 99%-plus performance or near-zero false rate without relevant evidence.

## Rehearsal gates
- Cold-start replay demo from documented commands without private data or API credentials.
- Real Muse connection, fit, warmup, arming and several deliberately performed gestures when the user is present.
- A natural-activity interval while speaking and watching the animation, with false activations recorded.
- Pause, seek, loop, late/duplicate gesture, stream loss/reconnection and unavailable API.
- Human audition on the actual output device: piano/bass/brush balance, believable suspense, clearly audible modulation, absence of abrupt clicks or unbearable transients.
- Exported performance matches the played sequence, within declared timing/renderer limits.

For subjective checks, record a simple human rating and a specific observation. Never state that the agent heard audio unless an actual listening-capable test occurred. Ask for bounded human audition actions through the app/runbook rather than pretending approval.

## Scope freeze
Keep one hero scene, one score, one brush groove and double-blink modulation polished. Hide unsupported gesture classes and unvalidated intensity control. Preserve the other prepared scenes/music as test assets or selectable extras only when they pass checks. No emotion detection, arbitrary-video reconstruction, universal music generator, large self-supervised model or generic plugin marketplace is needed.

## Event-day runbook
Use the planning budget in `.brief/README.md` only if the organizer allows the prepared materials. The plan must identify prepared code/data/models/music/renders and what is built during the event. If prior work is forbidden, document the smaller compliant version and do not misrepresent authorship or development time.

Provide a 60-90 second script explaining the geometry-to-score mapping, showing a near-miss/impact comparison and one genuine blink modulation. Keep a labelled real replay and a keyboard control ready. A fallback can demonstrate the composition system while honestly separating the failed hardware component.

## Final deliverables
A release checklist with PASS/FAIL/NOT_RUN, tested platform/browser/device versions, one reproducible command sequence, last-known-good artifact hashes, a privacy/license inventory, a concise known-limitations list, and a demonstration recording only if actually captured. Summarize measured performance without inflated claims. Do not force a success label; end with the real readiness status and the smallest remaining corrective task.
