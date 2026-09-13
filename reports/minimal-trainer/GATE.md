# Minimal personal trainer delivery — 2026-09-13

Implemented the user's B-only automatic training plan. Production trainer:
https://scenescore-muse-vertical.vercel.app/train/
Deployment: `dpl_72Liceq9qWrHPfrp2koJEhdb2jP5`, READY, production alias verified.
Only `/train/` changed in this publication. Fourteen non-training staged files
were preserved byte-for-byte. Sixteen public files were fetched and SHA-256
verified, including the existing studio JS/CSS, catalogue, bundles and videos;
`vercel.json` is deployment configuration and is not public. See
`deployment-manifest.json`, `deployment.json`, `published-verification.json`.

The studio checkpoint UI and companion integration are implemented and built
locally. They were not substituted for the existing hosted studio assets during
this trainer-only publication. Concurrent BLE, animation and library changes
were preserved. Some initial edits became part of a concurrent repository commit;
this report identifies the implemented behavior rather than treating the final
working-tree diff as the complete change.

## Behavior

One Train/Stop button, B-tap instruction, local-data notice and one status line.
The launcher authenticates; the trainer connects to the single compatible LSL
source. B acknowledgement follows storage, repeats are suppressed, delivery
failure and focus loss stop collection. Explicit synthetic mode is CLI/test-only.
Each click is capped at 600 seconds. Legacy reviewed collection APIs remain
available separately; no normal-page identifiers, checkboxes, charts or review
forms remain.

EEG-only two-second features feed the existing bounded classifier, gated by the
causal closed-double detector. Initial fitting requires 20 usable positives and
20 assumed-background windows. Further updates need ten new windows of each
class, start from retained weights and scaler, and use deterministic bounded
historical replay. Checks never feed fitting, preprocessing or threshold choice.
The complete configuration, scaler, weights, parent and data hashes are sealed
in immutable, atomic checkpoints before evaluation. Invalid numeric, hash,
configuration or source-contract artifacts cannot load; low or absent evaluation
never invalidates weights. Checkpoint versions remain available for rollback.

Fresh checks require 30 B labels, 120 monitored seconds and 60 seconds background.
Continuous decisions are matched one-to-one within B−1s to B+250ms. Extras and
misses are counted, including signal-related misses. The strict advisory target
is precision >.93 and recall >.93 with availability >=.95. Frequent false
predictions cannot postpone a failed check indefinitely. Failed checks return to
learning; each new checkpoint clears prior evaluation and starts a fresh check.
No model-generated labels are used. Results are explicitly B-label agreement,
with counts and incomplete-evidence state; missing evaluation is not zero.

Next Arm selects the latest compatible checkpoint regardless of evaluation,
resets on model switch, warms up and pins weights throughout the armed session.
Disarmed rollback supports an older compatible checkpoint or causal baseline.
Signal quality, single/triple rejection, gesture closure and musical approval
requirements remain. The exploratory B-only format does not fabricate hardware
verification or amend canonical contract 0.1. See decision
`docs/decisions/0015-minimal-personal-trainer.md` for authority and RAGTM lineage.

## Commands and outcomes

Passed:

- `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests services/bridge/tests modules/muse/training/tests modules/muse/baseline/tests modules/muse/runtime/tests`: 159 passed (`python-tests.log`).
- After the final check-loop correction, `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests/test_automatic.py`: nine passed, including the additional perpetual-false-detection regression (`automatic-final-tests.log`).
- `PYTHONPATH=.:src .venv/bin/python -m pytest -q modules/muse/acquisition/tests`: 124 passed, two skipped, two existing dependency deprecation warnings (`acquisition-tests.log`).
- `node --import tsx --test apps/training/tests/*.test.ts apps/web/src/muse/tests/*.test.ts`: 34 passed (`frontend-tests.log`).
- Root `tsc --noEmit` and `tsc -p apps/training/tsconfig.json`, focused Ruff checks and scoped `git diff --check` passed. Typecheck emits no output on success.
- Vite production builds for both trainer and studio passed. The studio retains a nonfatal >500 kB bundle warning. See `training-build.log` and `studio-build.log`.

Browser rehearsal used an isolated Playwright session `minimal-trainer`, with
explicit synthetic sources. A preparation fixture retained raw samples and
provenance for 19 positive and 49 background windows; one browser B tap completed
the first fitting minimum and produced a checkpoint. A repeated held B added
only one label. Stop retained the model and an incomplete check. A subsequent
run resumed the checkpoint; focus loss saved and stopped. A final fixture using
the completed artifact validator loaded a compatible seeded checkpoint, aborted
one B request deliberately, verified the unsaved-label error and automatic stop,
then verified focus-loss retention. The sole final-fixture console error was the
intentionally aborted request. Ten-minute timeout, interrupted writes, fresh
check boundaries and weight optimization were tested with bounded unit/API
fixtures rather than waiting ten minutes in a browser.

Desktop 1440×1000 and mobile 390×844 screenshots of the published page, plus
failure/focus-loss evidence, are in `output/playwright/minimal-trainer/`.
Chrome's shared automation surface was busy, so browser checks used the isolated
session. Loopback tests initially failed under the filesystem sandbox's socket
restriction; the authorized loopback-enabled reruns passed.

Not measured: real headset blink accuracy, physiological B timing, electrode
contact and independent participant/refit generalization. No 93% promise or
synthetic score is presented as real accuracy. No cloud training or raw EEG
upload occurred. This task does not resolve broader musical audition or phase
approval gates.

## Resource teardown

The bounded synthetic servers were PIDs 73428 (port 8768) and 84681 (port 8769).
The isolated Playwright browser PID was 77193. The first server expired normally;
the second received SIGINT, and the named browser session was closed. Exact PID
and port checks confirm all three exited and both test ports are free. All
integration-test fixtures joined their own workers/listeners. See `teardown.json`.

Final companion regression: five checkpoint tests passed after adding evaluation
refresh on the next Arm even when the selected checkpoint ID is unchanged
(`continuous-detector-tests.log`). The currently armed evaluation snapshot and
weights remain fixed. Companion Ruff checks also passed (`companion-lint.log`).
The two acquisition skips are explicitly opt-in physical Bluetooth diagnostic
and EEG streaming tests; no headset was accessed for this rehearsal.
