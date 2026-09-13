# Muse 05 — local semantic companion and training surface

Owned worktree: `/private/tmp/scenescore-muse-surface`, branch `codex/muse-surface`, base
`527f949`. No commit or merge performed. No changes to the shared shell, audio modules,
frozen contracts, root scripts or locks.

Implemented `apps/web/src/muse/MusePanel.tsx` with scoped CSS, frozen callback types,
ephemeral bridge client and pure state/clock helpers. Four explicit provenance labels:
KEYBOARD, SYNTHETIC_TEST, REAL_REPLAY and LIVE_MUSE. Live rendering requires actual verified
connected/good/warmed/armed state; selection alone falls back to KEYBOARD. A bridge failure
preserves keyboard and local synthetic control. Cue and prediction remain separate.
Feedback opens only after the cue and quiet interval; all locally stored notes remain
independent-review pending with truth_label:null, never predictive features or training
labels. Session split selection freezes when the local protocol session is prepared.
Local consent/retention/refit/negative-session guidance is visible. No raw recording or
upload starts from this UI. The active model/evaluation text makes absent real evidence
explicit. Parent supplies the exact action factory and existing audio dispatch.

Implemented `services/bridge` as a bounded stdlib HTTP server on 127.0.0.1:8766 only.
Exact origin/Host checks, origin-bound ephemeral bearer sessions, bounded bodies/paths,
narrow status/clock/arm/disarm/event API, at most eight handlers and four sessions, and
128 semantic events. A new handshake clears state; event overflow, source faults,
quality loss and a 1.2-second lost-subscriber lease disarm. HTTP never receives paths or
commands and never returns raw samples. Credentials are in memory and omitted from
access logs. Synthetic samples genuinely traverse CausalBaseline and its closure grammar.
Replay reads the local raw store lazily and preserves original bytes. No EEG recording
occurs. Optional exact-ID LSL stream resolution validates channels/rate/units before
consumption, closes its inlet and requires explicit local live-processing consent.

Live calibration dependency: the bridge now accepts `--quality-profile` and applies
`modules.muse.runtime.quality.QualityGate` before the causal detector. A missing profile
remains unverified; an ineligible profile fails before optional pylsl/stream acquisition.
Real streams require a hardware/config-bound profile from independently labelled,
consented real training sessions. Synthetic calibration cannot enable LIVE_MUSE. The
gate's causal numeric amplitude/variance/flatline/continuity checks are explicitly not
contact-impedance measurements. Stale samples disarm and reset. Calibration can enable
this implemented path without future integration code. No real Muse validation,
participant collection, learned training, human audition or physical output measurement
was performed in this node.

LSL descriptor verification fetches full inlet.info rather than abbreviated resolver
metadata. `services/bridge/lsl_clock.py` maps source clocks using liblsl's extended time
correction with its uncertainty, a measured LSL/Python monotonic midpoint and observed
offset drift. Clock resets invalidate the source. Synthetic/replay clock probes describe
the explicit local playback schedule, not physical capture timing. Browser rate mapping
requires two same-source/epoch anchors at least one second apart; it propagates anchor
uncertainty through 2.5-second validity and rejects above the shared 20-ms bound. Current
motion context is evaluated at the mapped request time. No unit-rate assumption or zero
uncertainty substitutes for a measured live clock. Quality/connection/source loss clears
browser anchors and requires recalibration.

Follow-up correction: browser fetch is explicitly bound to globalThis, avoiding the
Chrome Illegal invocation error found by the parent's integrated test. A targeted fetch
receiver test now covers authenticated handshake with the default browser fetch path.

Commands actually run:

- `./node_modules/.bin/tsc --noEmit`: passed after final UI change.
- `node --import tsx --test apps/web/src/muse/tests/state.test.ts`: 4 passed; all four
  mode labels/every live gate, delayed feedback truth separation, clock RTT/epochs.
- `PYTHONPATH=src:. .venv/bin/python -m pytest services/bridge/tests -q`: initial sandbox
  attempt had two socket permission failures and two passed; bounded loopback escalation
  approved, then **4 passed in 4.28s** on final clock/handshake behavior. Tests exercise
  authenticated API boundary, real paced synthetic EEG candidates/one closed double,
  disconnect/reset, event overflow and no raw sample response.
- `.venv/bin/ruff check services/bridge`: passed. Three lambda assignment lint failures
  were fixed with `functools.partial`; CLI `--help` then passed.
- `PYTHONPATH=src:. .venv/bin/python -m compileall -q services/bridge`: passed before
  the final mechanical lint adjustment; Python CLI import passed after that adjustment.
- Playwright skill read; `npx` exists. CLI `--session muse-surface --help` bootstrap
  hung without output under restricted network and was cancelled (session 87766 exit130).
  Read-only process verification confirmed no `playwright-cli` child remained. Existing
  unrelated Playwright MCP processes were untouched. Browser checks handed to the parent
  to avoid conflicting with its active browser session.

Not run here: integrated production build, deployed UI, browser audio acknowledgement and
key arrival, browser mode/feedback interactions. Parent owns these integration checks.
Passing software tests is PIPELINE_TESTED_ONLY evidence; no detector accuracy claim.

Resource cleanup: source and HTTP jobs existed only inside bounded pytest functions;
each is joined and asserted no longer alive in `finally`. No running server, capture,
container, watcher, browser or dependency install was retained. The CLI bootstrap was
cancelled and its exit checked. Worktree-only node_modules/.venv symlinks point to the
existing root dependencies; do not stage/copy these links.

Integration and exact CLI: `docs/requests/muse-05/shell-integration.md` and
`services/bridge/README.md`. Copy only these owned files (exclude Python caches):

- `apps/web/src/muse/MusePanel.tsx`
- `apps/web/src/muse/types.ts`
- `apps/web/src/muse/state.ts`
- `apps/web/src/muse/bridge.ts`
- `apps/web/src/muse/muse.css`
- `apps/web/src/muse/tests/state.test.ts`
- `apps/web/public/muse/README.md`
- `services/bridge/__init__.py`
- `services/bridge/__main__.py`
- `services/bridge/server.py`
- `services/bridge/lsl_clock.py`
- `services/bridge/README.md`
- `services/bridge/tests/test_bridge.py`
- `services/bridge/tests/test_lsl_clock.py`
- `docs/requests/muse-05/shell-integration.md`
- `handoffs/muse-05.md`

Follow-up exact validation (2026-09-13):

- `PYTHONPATH=/private/tmp/scenescore-muse-runtime:src:. .venv/bin/python -m pytest services/bridge/tests/test_lsl_clock.py services/bridge/tests/test_bridge.py -k 'not origin_host and not reconnect_and' -q`: 8 passed, 2 deselected. Uses the runtime worker's actual quality module read-only; includes synthetic-profile refusal before real LSL, mocked LSL full metadata/quality/closure wiring, stale quality disarm and native clock arithmetic.
- `node --import tsx --test apps/web/src/muse/tests/state.test.ts`: 4 passed after fetch/rate changes.
- `./node_modules/.bin/tsc --noEmit` and `.venv/bin/ruff check services/bridge`: passed.
- Shared parent browser results and deployment evidence remain owned by the integrator.

- Full final suite: `PYTHONPATH=/private/tmp/scenescore-muse-runtime:src:. .venv/bin/python -m pytest services/bridge/tests -q`: **10 passed in 4.78s**, approved bounded loopback escalation. Mock-LSL only; no real acquisition. All temporary threads joined and exit assertions passed.
