# Node 03 integration note — no shared-schema change

Consume `modules.music.ornament.apply_transforms` during offline preparation after
`resolve_events` and before exact approval hashing. It returns canonical schema-0.1
events plus a module-versioned audit. Store both event and audit hashes; reusing an
old approval after changing requests, seed or prepared events is invalid.

Node 04 owns time-indexed intent selection, near-miss harmony withholding, object
assignment and policy-to-request mapping. A grace request steals from the leading
edge of the selected source slot; a within-slot contact is not moved or guessed by
this API. The caller must select eligible source material and record quantization.
Every suppression has a reason; missing motion data should remain the caller's
explicit unmodified-source fallback.

Node 06 owns browser articulation envelopes. The typed layer accepts detached,
staccato, tenuto and legato without changing occupied duration or other controls.
The existing Python renderer distinguishes legato only; its A/B evidence deliberately
uses grace/velocity/legato. Broader Python articulation rendering, if later needed,
requires the renderer owner's versioned change and fresh evidence. It is not a
prerequisite for the presently authorized browser implementation, and this note
does not authorize changes outside the node's ownership.

All protected brushes and scene-time Foley remain byte-identical. Optional runs and
duration-extending transforms remain disabled. Machine GO does not grant a human
audition or plan-approval verdict; see `handoffs/music-03.md` for exact evidence.
