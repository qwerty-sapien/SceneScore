# 00 — verify lineage, choose the transport, freeze the architecture

**Owns:** `docs/decisions/`, `handoffs/`. Writes no implementation code beyond a throwaway
diagnostic. **Budget:** 25 minutes.

`modules/muse/baseline/LINEAGE.md` already records the RAGTM inspection, hashes, licence
copy, ported defaults and the oracle test's exact scope. Do not redo that audit. Confirm
it still holds and answer the question it leaves open: **how does this machine actually
reach this headset, today.**

## Verify

1. `LINEAGE.md` and `lineage.json` still match the nested `RageAgainstTheMachine-main/`
   source, and it is still unmodified.
2. `modules/muse/baseline/tests/ragtm_oracle.mjs` still passes, and you can state in one
   sentence what it establishes and three things it does not.
3. `causal.py::Config` defaults still match `REPO_BASELINE.md`. Any drift changes the
   latency arithmetic in `examples/latency_ladder.json` and must be reported as a latency
   change, not only a config change.
4. `reports/03A/MODEL_CARD.md` still says `INSUFFICIENT_REAL_DATA` with zero deployment
   models — or, if that has changed, this pack's evaluation plan changes with it.

## Discover the real hardware facts

`docs/VISION.md` lists Muse generation, transport, channels, units, rate and Bluetooth
permission as unresolved. The RAGTM source declares TP9/AF7/AF8/TP10 at 256 Hz; that is a
statement about someone else's headset. Run the smallest diagnostic that answers, for
**this** device: generation and firmware, transport actually available (BLE, LSL via a
bridge, or neither), channel names and order as reported by the device, units, verified
sample rate measured rather than declared, and whether macOS Bluetooth permission is
granted to the process that needs it.

Every one of those answers is recorded as measured or as unavailable. A remembered default
written down as a fact is the defect this section exists to prevent.

## Choose and record

One decision record in `docs/decisions/` containing:

- **Transport**: the chosen route, the evidence it works on this machine and browser, and
  the fallback. If nothing connects, say so plainly and set the whole live track to
  blocked; the replay and simulated tracks proceed unblocked.
- **Deployment shape**: where the surface is hosted, where acquisition runs, and the exact
  boundary between them. If a local companion bridge is chosen, record its loopback
  binding, handshake and command scope now, before node 05 builds it.
- **Participant availability**: whether a consenting participant exists in this timebox.
  This single answer determines whether node 04 produces `REAL_DATA_EXPLORATORY` or
  `PIPELINE_TESTED_ONLY`, and it is better decided now than discovered at hour five.
- **Write-scope confirmation** against files that actually exist, resolving any collision
  before 01 and 02 start in parallel.

## Forbidden

Rewriting code in this node. Importing game code from RAGTM. Copying its clock or upload
behaviours — `LINEAGE.md` flags both as defects not to inherit. Adding its ML stack to the
root locks. Claiming a transport works because it worked in a different project.

## Done when

A reader knows what hardware exists, how it is reached, what is blocked, whether a
participant is available, and which claims this run will be able to make.
