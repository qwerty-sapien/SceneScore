# Muse semantic runtime, version 1

`RuntimeAdapter` wraps the existing unchanged `Config`/`Grammar`, gates stream
faults and produces frozen 0.1 `ControlAction` records. It starts no process,
performs no I/O, and imports no EEG transport or ML runtime. Real acquisition
still requires independently verified acquisition metadata. Synthetic controls
establish software behavior only.

The supplement envelope is exactly:

```ts
type MuseControlEnvelope = {
  version: 'muse-control-envelope-1';
  action: ControlAction;
  detector: {version: string; model_version: string; grammar_hash: string};
  timing: {
    t0_final_blink_s: number; t1_decision_s: number; t2_dispatch_s: number;
    t3_request_s: number; t4_received_s: number | null;
    t5_ack_onset_s: number | null; t6_boundary_s: number | null;
    device_epoch: string; host_epoch: string; audio_epoch: string;
    clock_mapping_id: string; unavailable_reasons: Record<string,string>;
  };
};
```

No samples, amplitudes or arbitrary model payloads cross this boundary. Canonical
provenance uses `real_device`, `replay`, `synthetic`, `keyboard`; uppercase mode
names are visible UI labels only. `detector.model_version` is diagnostic lineage,
not evidence that a model was trained or validated. The generated synthetic
example is `tests/control-envelope.json`.

Instantiate `RuntimeAdapter(metadata, device_epoch, config=Config(),
started_device_s=0, model_version='scenescore-new-causal-median/1')` and configure
with `MusicContext(approved_plan_hash, scene_policy_id, signed_semitones, lanes,
expires_after_s=6, suppression_reason=None)`, a validated canonical device-to-audio
`ClockMapping`, and an explicit host epoch. The music owner supplies direction
and lane/plan context **evaluated at the mapped decision timestamp**; an old sign
cached before a gesture is not sufficient. Runtime never infers direction or
synthesizes approval. Missing approval or stationary geometry produces a visibly
suppressed canonical control.

`arm(device_now_s)` requires completed warmup. `feed(candidate, host_now_s)` and
`advance(device_now_s, host_now_s)` return lists of `{envelope, reason}` results.
Alternatively `accept(gesture, host_now_s)` accepts a closed GestureEvent from
the actual causal baseline and returns one result. `fault(reason, device_now_s)`
clears partial grammar, disarms and restarts warmup for dropout, quality loss,
reconnect, refit, model reload or stream discontinuity. `disarm(device_now_s)`
does the same for an explicit user disarm. Dedupe IDs survive faults/rearm; after
4096 candidates or sequences the session must be replaced instead of silently
forgetting identifiers. Rejected events are consumed and cannot later be retried.

The Python adapter is a local synchronous integration reference. A loopback
companion should forward semantic GestureEvents, not stale preconstructed music
contexts. The browser audio owner maps their decision times, evaluates the current
trusted music context, and dispatches via the same canonical validation path as
keyboard. Any bridge transfer is measured separately; it is not a claim of a
network-free or sub-5-ms path. No simulator may label itself live.

ClockMapping validity windows are source-clock seconds. Two measured anchor pairs
define the affine rate and offset; the conversion requires the exact domains and
epochs and rejects uncertainty above 20 ms (a runtime bound, not a measured
hardware result). t0 is the canonical final blink **end**, t1 is closure decision,
t2 is host monotonic construction, and t3 is mapped **t1**, never mapped t0.
Never subtract t2-t1 without a device-to-host mapping. The existing music
`Decision.boundary_s` is scene time and denotes a pivot, not the later tonic
arrival. `attach_receipt` consumes explicit `audio_received_s`,
`ack_onset_audio_s`, and `arrival_audio_s`; absent engine stamps stay null.
All onsets are scheduled, not acoustic; no loopback measurement is implied.

The immutable prompt-pack examples use incompatible onset-to-onset gaps and an
onset-based t0. See `evaluation/grammar-semantics-v1.json` and the scoped request
for exact discrepancies. Runtime retains the repository's end-to-next-onset
gap and strict closure after final-end + max_gap. It does not claim the original
14 cases agree with the repository grammar.
