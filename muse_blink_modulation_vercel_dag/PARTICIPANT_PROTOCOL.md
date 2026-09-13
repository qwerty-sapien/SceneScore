# Participant protocol

Binding on any node that records a person. If no consenting participant is available in
the timebox, every node still runs — on replay and fixtures — and the pack reports
`PIPELINE_TESTED_ONLY`. Recording someone without this protocol is worse than shipping no
real data.

## Consent

Recorded before the first session, in the participant's own words or on a signed form:
what is collected (frontal EEG, optional IMU, timestamps), where it is stored (this
machine, this repo's local store, not uploaded), how long it is kept, and that they can
stop at any moment and have the session deleted without giving a reason. Consent to
collect is not consent to publish; a demo shown to an audience needs its own yes.

Stop immediately on request, on discomfort, or on any sign the headset is irritating. This
is a music instrument, not a study, and nothing here is a clinical or diagnostic procedure.
Do not interpret, store or discuss any EEG signal as a health, mental-state, emotional or
cognitive indicator — the repo's own framing is an ocular-gesture control, and it stays
that way.

## Labels must be independent of the detector

Prompt timing is not proof a gesture happened. An annotation source derived from detector
output is circular and invalidates every number computed from it.

- Use a synchronized independent observation — a video or a second observer — with its own
  consent, or delayed participant self-report reviewed against the raw trace.
- Labels are `performed`, `missed`, `uncertain`, or natural negative. `uncertain` is a real
  category; do not collapse it to make counts look better.
- **No simultaneous motor confirmation.** A button press during the gesture leaks motor
  artifact into the very window being labelled. Confirm afterwards.
- Cue state and prediction state are displayed and stored separately, always.

## Session shape

Many short independent sessions, not one long recording. At least one deliberate headset
removal and refit, because refit is the dominant real-world failure and a model that has
never seen one is untested. Record natural activity — talking, looking around, ordinary
blinking — as explicit negatives, with its exposure duration logged. Natural blink clusters
genuinely resemble deliberate gestures; the protocol does not assume intent is separable.

## Splits

Split by complete session and refit before any windowing. Assign train, development and
final-test membership **before** comparing models. Fit preprocessing, thresholds and
grammar on development data only. The final test set is immutable: a failed final test
motivates newly collected independent data, never retrospective tuning.

## Data locality

Raw samples and timestamps stay on this machine, unmodified, and are preserved alongside
any derived feature. No upload to a deployed site or third party without a separate,
explicit, individually justified opt-in. Conversions are recorded separately from the raw
data; the raw data is never overwritten in place.

Deleting a session on request means deleting derived artifacts too.
