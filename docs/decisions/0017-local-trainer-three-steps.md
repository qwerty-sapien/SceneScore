# Local connection, EEG check, then training

Authority: the user's 2026-09-13 correction that the trainer does not need Vercel
and must work locally, with connection first, measurable EEG second, training
third. B is pressed once within one second after completing a double blink.

The launcher serves an authenticated page on 127.0.0.1. Connect opens the local
headset source; an in-memory check requires fresh, continuous, varying frontal
samples before the separate Train action becomes available. No preflight sample
is recorded or fitted. An existing compatible LSL stream is reused; otherwise a
trainer-owned adapter uses the shared classic Muse Bluetooth manager. The source
is handed directly to training after the check rather than opening a second
headset connection. Check evidence is saved with the eventual exploratory run.

Stop, cancelled setup, failure, focus loss and shutdown retain trained models.
Weights remain local and 93% remains advisory under decision 0015. This correction
changes the delivery/setup experience, not the fixed B-label matching tolerance,
independent evaluation semantics, production quality gates or contract 0.1.
A B tap is still a user report; its timing cannot certify the physiological
blink or be used as a predictive feature. The old deployment report is historical
and the Vercel page is no longer the supported entry point.

Connection follow-up: the user supplied a BrainFlow 5.22.2 script with board 38
and a 15-second discovery timeout that reported Muse-AD3C, while the trainer's
Bleak scan did not find it. Use that BrainFlow setup for direct trainer Bluetooth.
The supplied output establishes discovery only, not successful streaming. Native
calls run in an owned helper process with bounded waits and cancellation;
actual EEG and original BrainFlow timestamp values remain local and unchanged.
The shared studio BLE path is unaffected. The existing Bleak adapter remains
available for injected developer use; no second scanner runs automatically.

Subsequent correction: the standalone script never returned from prepare_session.
Its live stack (PID 90889, launched 14:29:44) confirmed two threads deadlocked:
the main thread unregistering the scan callback waited for SimpleBLE's callback
mutex while the callback waited for BrainFlow's global wrapper mutex. The exact
abandoned process was stopped. Direct acquisition now uses the shared Bleak
adapter in the bounded helper, with a 15-second scan and explicit progress. This
supersedes the BrainFlow default above; that adapter remains developer-only.
No timeout increase is represented as a fix to the native deadlock.
