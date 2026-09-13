# 0011 — Muse blink-to-harmony vertical

Authority: the current user's request to initiate the full Muse EEG → blink → chord
progression/key-change flow in parallel, with human assistance reserved for blink
training. The supplied START prompt is an execution reference within that scope.
This authorizes implementation/integration; it does not invent participant consent,
real observations, human musical audition, or exact human plan approval.

## Captured baseline and architecture

Base Git revision: `527f949fbf10319b84428b1cf510c5d2c1c205d2`.
The five RAGTM source hashes in `modules/muse/baseline/lineage.json` match;
the 20 baseline tests pass, including numerical oracle parity. This establishes
the tested numerical candidate subset, not detection accuracy, hardware transport,
or complete original-pipeline equivalence. Default detector configuration is unchanged.
The two supplied pack interface files are byte-identical.

At initiation the project environment contains none of pylsl, bleak, muselsl or
brainflow, and the private store contains zero session manifests. The real detector
status remains `INSUFFICIENT_REAL_DATA` with zero deployed learned models. Headset
generation, firmware, device-reported channels/units, measured rate and Bluetooth
permission are unavailable; these are current blockers, not immutable host facts.
No participant recording begins until explicit collection consent and independent
annotation provisions exist. Availability is pending the training-step response.

Acquisition runs in an explicit-start local companion, bound to `127.0.0.1:8766`.
The browser owns audio time and music execution. The companion uses a short-lived
random token, exact allowed origins, bounded messages/queues and narrow commands;
it does not execute arbitrary commands or serve arbitrary paths. No public bind or
raw EEG publication. A deployed static surface must load without the companion;
keyboard and clearly labelled synthetic/replay modes remain usable. Live support
is unverified until a real transport and device metadata are measured. Direct
browser BLE is not selected without an actual working-device test.

## Seam precedence and evidence

Frozen contract 0.1 wins over pack shorthand: canonical provenance uses
`real_device`, `replay`, `synthetic`, `keyboard`; uppercase values are UI labels.
Extra detector/model/ladder fields belong in a versioned envelope, not canonical
ControlAction. Geometry supplies the signed direction; runtime never infers it
from EEG. The browser submits every source through the same audio entry point.
The local companion transfer is explicit interprocess transport; after browser
acceptance no external service, model or network request participates in audio
execution. Transfer and clock uncertainty are reported separately.

The supplied grammar examples measure blink separation from onset, whereas the
existing repository grammar measures from candidate end to subsequent onset.
The pack's ladder example calls t0 onset, while the repository GestureEvent uses
candidate end as final_blink. Preserve immutable inputs and existing semantics;
record conflicting examples and version any corrected executable cases. Closure
latency is reported from the actual declared final-blink timestamp; no headline
claim may hide waveform duration or equate algorithmic timing with physical blink.

The user's request permits automated preparation and execution of an explicitly
unapproved draft demonstration. Such runs retain `approval:null` and
`AUDITION_PENDING`; they do not become approved performances, and cannot satisfy
formal approval/audition gates. Exact human-approved performance remains a
separate capability. This keeps the requested unattended software work moving
without fabricating a human decision.

## Ownership

Three isolated worktrees from the captured base: `codex/muse-runtime` owns runtime
and evaluation supplements; `codex/muse-acquisition` owns acquisition, annotation,
baseline and training; `codex/muse-surface` owns the Muse UI subtree and local bridge.
The integrator owns shell mounting, audio changes, root entrypoints, shared tests,
decision records and final evidence. Existing Blender work is outside this task.
Workers do not merge or overwrite shared files. No frozen schema/lock amendment
is planned. Final claims require exact-code verification and task-job teardown.
