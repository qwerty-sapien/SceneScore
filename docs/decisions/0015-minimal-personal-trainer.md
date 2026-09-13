# Minimal trainer and advisory production use

Authority: the user's explicit implementation plan of 2026-09-13 and preceding
clarification that weights below 93% must remain usable and improvable.

Adopt one Train/Stop control, B-tap reports, local-only processing and automatic
bounded supervised fitting interleaved with fresh frozen-detector checks. The
93% precision/recall target guides stopping; it is not an artifact retention or
production eligibility gate. The next Arm uses the latest compatible saved
checkpoint, pinned for the armed session. Explicit older-checkpoint/baseline
rollback remains available. Numerical integrity and compatibility remain gates.

This decision supersedes earlier personal-model production restrictions only
for this explicitly authorized B-only path. It does not amend frozen schema
0.1, independently reviewed evaluation semantics, musical-plan approval,
stream-quality requirements or single/triple rejection. B-only records use
`scenescore.automatic-blink-run/1`; no operator or hardware verification is
invented. Agreement with B reports is not independent accuracy evidence.

Reference inspected read-only: RAGTM backend `mi.zip`, SHA-256
`f4d8d7aba5efe28c92fec50a3d1af78d009fdc4c7f2f323d52d5099903d7f19e`.
Its 17 files match the extracted `mi` tree. The module is motor-imagery code;
its model file is a Git LFS pointer. Reuse collection/buffering, quality checks,
bounded fitting and persistence patterns, not its class definitions or weights.
The actual frontend blink detector in `frontend/src/hooks/useBCIStream.ts`
remains the reference through SceneScore's existing RAGTM candidate port.
SceneScore's causal candidates, closed-double grammar and two-second EEG-only
classifier compose the personal detector. No game code was imported.
