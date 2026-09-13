# Runtime integration request — immutable example discrepancies

Authority: current user authorized the Muse vertical; frozen contract 0.1 and
unchanged `modules/muse/baseline/causal.py::Config/Grammar` remain authoritative.

The new module supplement `muse-control-envelope-1` wraps a canonical control
and separately named detector/model/clock diagnostics. It changes no shared
schema, lane semantics, grammar threshold, approval rule or music policy. The
music owner must provide context evaluated at the mapped decision timestamp.
The browser should receive a semantic gesture from the companion, map its clock,
obtain that trusted context, and call the same validated `Timeline.submit` path
as keyboard. Raw EEG must remain local. A bridge transfer is an actual transport
interval to measure; it cannot honestly be described as network-free.

The prompt pack's reference checker passes its own 14 cases, but it models gaps
between onsets. The repository models previous-end to next-onset gaps. Running
the original cases through the runtime adapter gives **11/14 agreement with the
pack**, while all 14 match documented repository expectations:

| Case | Pack | Repository | Reason |
|---|---|---|---|
| P2 | 1 action | 0 | 0.12 onset gap minus 0.05 duration leaves 0.07, below 0.10 minimum. |
| N3 | 0 | 1 | 0.60 onset gap minus 0.12 duration leaves 0.48, below 0.50 maximum. |
| N8 | 1 | 0 | Third onset 2.90 occurs before closure after 2.92; all four form one train. |

`modules/muse/evaluation/grammar-semantics-v1.json` contains an independently
explained corrected set outside immutable inputs: P2's second onset is 2.16;
N3's is 2.64; N8's second pair uses 2.95/3.22. These give the intended positive,
separate-single, and cooldown behaviors under repository semantics. All other
case timestamps are preserved. The corrected set passes 14/14. The reference
checker was executed on an exact temporary copy so its output-writing behavior
did not mutate the attached pack.

The pack calls t0 the final onset, but canonical `GestureEvent.final_blink` is
the final end. P1 closure is strictly after 2.92, not 2.80. Closure has a 500 ms
floor measured from final end; no claim hides that delay. t2 is host monotonic
and t1 is device time, so their difference remains null without an independently
validated device-to-host mapping.

Existing `Decision.boundary_s` is scene time for the harmonic pivot. Requested
music-owner supplement fields are `ack_onset_audio_s` and `arrival_audio_s`,
where arrival is the actual scheduled tonic establishment. The runtime receipt
helper accepts only explicit audio stamps and leaves missing values null.
Scheduled onset does not establish acoustic latency or human audition.

Affected tests: runtime grammar/fault/clock/duplicate tests, four-source TS
conformance and Timeline rejection/flood tests, and downstream bridge/music
integration. No canonical migration is needed; JSON envelope version 1 and the
corrected fixture supplement must be accepted by the integrator. No hardware,
real-data, physical-audio or statistical detector claim is requested.
