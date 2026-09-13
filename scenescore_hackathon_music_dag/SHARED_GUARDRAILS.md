# Shared guardrails — animation-to-music vertical

Every node obeys all of these. A node may add constraints; none may relax one.

## Authority and truthful evidence

`AGENTS.md`, `docs/VISION.md`, `docs/CONTRACTS.md`, `docs/EVALUATION.md` and the user's
current instruction outrank this pack. Where this pack and a repo document disagree, the
repo document wins and the conflict is recorded, not silently resolved.

Schema validity is not audition. A passing test is not a listening judgment. A hash match
is not human approval. A model's opinion of a rendered file is not perception. Sampled
stills are not motion. Every claim names the exact asset, config and source hash it
assessed, and distinguishes passed, failed, blocked and not run. Mark `real_device`,
`replay`, `synthetic`, `cached_gpt`, `manual_plan` and `keyboard` as independent
provenance dimensions, never collapsed into one label.

Never present synthetic fixtures as real evidence. Never train, tune or fit against a
final-test artifact. Never fabricate a zero for an unavailable measure; use null with a
reason.

## Contract discipline

`contracts/0.1/schema.json` is frozen. Geometry-rich summaries, arranger `Policy` and the
new rebound descriptor are **module-versioned supplements**, not extra fields silently
added to canonical records. A change to meaning or required fields needs a migration,
fixture updates and an integrator decision recorded in `docs/requests/<node>/`.

Times are seconds with named clock domains and epochs; diagnostic latencies are
milliseconds. Scene time zero is the declared start frame. World space is right-handed
XYZ, Z up, metres. Quaternions are xyzw. Unknown references, incompatible major versions,
non-finite values and unit ambiguity are errors.

## Musical identity

The soundtrack is original blues/ragtime-derived swing with restrained bossa colour, per
`docs/VISION.md`. The named inspirations are creative traits, never copied tunes,
arrangements or artist emulation. Do not download third-party MIDI. Do not introduce a
composition whose provenance is not recorded with a hash.

Overwhelmingly, note identity and placement come from the existing symbolic source.
Transformation is performance, not composition: it changes articulation, voicing, groove,
density and register. It does not rewrite the melody, does not change meter, and does not
alter bar topology. Any ornament declares whether it preserves the occupied duration;
those that do are the default path.

Key, chord, register, dynamics, articulation, phrasing, ornamentation and timbre remain
independent controls. Changing one must not move another as a side effect. Unpitched
brushes are never transposed. Foley is a separate scene-second stream, never quantized
into the soundtrack's tick grid and never counted against its event budget.

## Bounded generation

The creative layer is small, seeded and reproducible. Allowed pitches derive from the
current key and chord plus a declared pentatonic, blues and chromatic-approach rule set.
No free random note generation. Every transform is seedable and produces identical output
for a fixed seed, input and version.

Required invariants, tested: no note outside its allowed slot unless explicitly marked; no
zero, negative or malformed durations; no hanging notes; stable total score duration;
bounded event-density increase; MIDI and renderer values in range; swing applied exactly
once to eligible events; register bounds respected after every transposition.

Guard against the failure modes that make bounded generation sound bad anyway: muddy
low-register clusters, simultaneous stacked ornaments, mechanical repetition of the same
decoration, and density that removes the space the style depends on.

## Motion semantics

Consume evaluated animation output. No computer vision, no learned embeddings, no emotion
or intent inference from geometry. Gap and area are geometric proxies: no impulse, force,
mass, momentum or energy is inferred from them, and a descriptor that could be read that
way must carry an explicit disclaimer field.

Proximity is not impact. A near miss requires an independent bracketed positive minimum
and a certified no-tunnelling segment. Screen-space size is not world-space size. A
rotating body's world AABB changes when its shape does not.

Missing or out-of-coverage inputs fall back to the unmodified score with a logged reason.
Silence on missing data; never an invented default.

## The live control path

Between an accepted control and the scheduled acknowledgement there is no network call, no
model, no LLM, no disk read, no unbounded search and no recompilation. The transition is
an O(1) lookup in a frozen table plus a bounded voicing application. See
`INTERFACE_CONTRACT.md`; its ownership table and latency ladder bind every node here.

Keyboard, synthetic, replay and live events reach the same entry point through the same
validation. A shortcut that exists only on one path invalidates the claims made about the
others.

One pending request at a time. Repeated events cannot queue a cascade. Pause clears
pending controls. Expired actions are dropped with a reason, never executed late.

## Approval and audition

`TransitionPreview` is unapproved audition data. `ApprovedSession` requires exact payload
bytes, an approval decision and current input hashes. Editing a plan or changing an asset
invalidates approval. An automated identity clicking an approve button is not human
approval and must be refused, not worked around. Draft exports carry `approval: null` and
`audition_status: AUDITION_PENDING` until a named human records a verdict with a date and
an asset hash.

## Timing claims

Report the `INTERFACE_CONTRACT.md` ladder intervals separately. "Sub-300 ms" may describe
only accepted control to scheduled audible onset. A scheduled onset is not an acoustic
onset. The musical boundary wait is intentional, disclosed, and never folded into a
detector or responsiveness number. Do not claim precision finer than the source cadence
allows — the current source is 8 fps.

## Ownership

Each node writes only the paths its prompt lists, plus its own handoff and
`docs/requests/<node>/`. Shared schemas, root scripts and locks, service mounting, shared
status and evaluation thresholds belong to the integrator. Do not revert another node's
edits or auto-resolve merge conflicts. Parallelize only with genuinely disjoint write
scopes.

## Resource discipline

Reuse the repo's own budget helpers. Record the exact identity of any persistent job,
terminate its children and verify exit. Never kill unrelated jobs. Keep expensive renders
out of long blocking calls. Render at low quality and final cadence first; spend final
compute only after the musical gate.
