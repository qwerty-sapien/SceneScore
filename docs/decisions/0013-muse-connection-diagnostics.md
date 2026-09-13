# Active Muse connection diagnostics

The user requests active detection and fault isolation for Muse hardware and EEG.
After local service authentication, the webpage now starts bounded metadata-only
checks every ten seconds and polls current sample health every second. A pause
control stops discovery; checks stop when the browser stops polling. No connection,
pairing, recording or Bluetooth permission request occurs automatically.

Keep Bluetooth permission/power, Muse-service advertising/system connection, LSL
EEG outlet discovery, descriptor compatibility, selected inlet, sample arrival,
and continuity as separate evidence. An unknown or stale check never becomes a
green result. Streaming data may remain usable even if direct Bluetooth inspection
is unavailable; LSL does not expose the underlying transport's connection state.

A bounded native CoreBluetooth helper observes the Muse FE8D service only. It never
connects or reads characteristics. Requesting macOS Bluetooth permission requires
the webpage's explicit Enable Bluetooth check action. OS permission and physical
device facts cannot be invented or replaced by an LSL/synthetic result.

Sample freshness uses host batch receipt age: 0.5 seconds marks fresh diagnostics;
the existing two-second source timeout remains separate. Rate mismatch reuses the
existing 2% recording-readiness check. Constant values and timestamp gaps are
observations, not a physiological or electrode-contact diagnosis. Reports contain
metadata and summary values only, with no raw samples, tokens or .env contents.

MUSE_TRANSPORT, MUSE_BOARD_ID and MUSE_UNITS exist only as unused .env placeholders
in the current trainer. It uses LSL, no BrainFlow board ID, and descriptor units.
No credentials file or frozen schema/lock is modified.
