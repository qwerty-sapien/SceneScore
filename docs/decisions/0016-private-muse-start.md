# Private local Muse workflow

On 2026-09-13 the user explicitly instructed Codex to process and record the
nearby Muse locally without another confirmation or consent discussion.

An explicit `make muse-live` invocation therefore starts the local processing
workflow without an additional question. The launcher creates the existing
bridge CLI's private startup record automatically and removes it on exit.
The standalone streaming diagnostic no longer requires a separate file.

Actual raw recording uses the separate explicit diagnostic `--record` command,
with a fresh path under Git-ignored `private_data/`. It preserves canonical
AF7/AF8 samples, original clocks and gaps using the existing Recorder. The
website and HTTP companion have no raw recording API. This decision changes no
quality, clock, evaluation or accuracy gate.

Concurrent training and shared server/UI files remain owned by the other task;
this change uses the launcher's existing server CLI contract. Follow-up diffs
must respect `docs/requests/muse-ble/concurrent-training-followup.md`.
