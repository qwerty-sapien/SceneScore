# Manual prepared key-change button

Authority: the user's 2026-09-13 request to exercise key changes with chord
progression independently of the EEG classifier, using a random appropriate
manual change and hiding the button when Muse is detected.

The integrator owns this bounded web/audio integration. Normal draft playback
now exposes **Change key**, without requiring the separate conducting demo or
arming the detector. A click selects one feasible prepared ±2 edge from the
current key using a recorded unsigned 32-bit seed. It overrides the scene's
motion sign for this explicit manual request only. The canonical action remains
keyboard provenance, with `manual-prepared-choice-1` identifying the selection
policy. Its scene-policy field continues to bind the loaded plan; it is not
evidence of measured directional motion. This is an explicit exception to
VISION's default geometry selection, not a change to live gesture semantics.

The existing dispatcher, scheduler, expiry, one-pending-request limit, register
bounds and transport resets still apply. The button is disabled when paused,
preparation is incomplete, a transition is pending or no transition fits before
the ending. It creates neither approval nor an armed live-input context. Draft
exports retain approval:null and contain the manual action/seed in their traces.

Detection uses the authenticated companion's scan results or live hardware
connection status, independently of detector arming and quality. Selecting
LIVE_MUSE alone, synthetic samples and replay do not count as detection. The
button returns after disconnect or companion loss. Browser-only use cannot
passively scan Bluetooth; detection begins through the existing companion and
Scan for Muse flow. No new headset service or automatic capture starts.

The standard transition compiler now treats `piano-comp-0/1/2` as harmonic
voices alongside existing `harmony-0/1/2`, resolving the library piano and bass
through the same dominant-to-tonic bar. Guitar/object motifs transpose, and
brushes, Foley, gain, articulation and expression remain independent. The
display follows the prepared harmonic bar through rests and transposes later
source chords. Frozen schema 0.1, source media and existing review samples are
unchanged; the duet regression now expects reharmonization during the transition
bar and ordinary transposition outside it.

Evidence: [manual key-change report](../../reports/manual-key-change/REPORT.md).
This checks the software music path; it does not establish real EEG classifier
accuracy, live clock/signal reliability, human audition or physical output timing.
