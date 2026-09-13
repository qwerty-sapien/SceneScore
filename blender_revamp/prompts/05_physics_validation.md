# 05: independently validate finalized scene motion

Depends on 04 and 03. Own validation/evidence, not production motion. Read the actual `.blend`, cache and evaluated transforms as well as sidecars. Use an independent review context where supported.

Execute positive controls, negative controls, production mutation tests and candidate validation. Inspect all physically relevant bodies, including silent supports and off-camera colliders that can influence visible action.

Confirm:

- No conspicuous interpenetration or tunnelling; tolerances are justified for geometry, scale and solver resolution. Rotated/contained solids are handled correctly. Increase solver resolution and check convergence where contacts are marginal.
- Held objects match the actor/mechanism, release state is continuous and unpowered free-flight acceleration agrees with the configured forces within numerical error. No geometry scale drift; inspect world-transform scale or rigid shape invariants rather than world AABB size alone.
- Impacts occur after genuine contact, response fits the declared masses/materials, and secondary collisions/support loss explain subsequent motion. A low-recoil or zero-recoil result is evaluated against its mechanics, not automatically rejected.
- Initial stack stability, launch-disabled stability and matched-near-miss target stability. Visible resting objects have actual support; decreasing motion settles without arbitrary freezing, premature sleep or perpetual jitter.
- Fresh-process replay of the baked asset reproduces event timing and trajectories within recorded tolerance. Changing physics invalidates the cache and downstream evidence. Rendered event frames correspond to the exported state/timestamps.

Produce actual diagnostic clips for each small positive/negative regression scene and the hero/control. Inspect normal cadence and event windows with contact proxies available. Log native frame rate, frame indices, source/bake identities and any perceptual access limits.

For a failure, provide the exact object pair, interval, measured value and a minimal repair request to 04. Do not loosen gates or alter expected results to make the candidate pass. Repeat within the agreed budget.

Pass only the physical gate here. Attractive staging and musical quality remain separate. Report how many positive cases were accepted and how many intentionally bad cases were rejected, naming any unexpected result. No unsupported claims of perfect numerical impenetrability or cross-platform bit-for-bit simulation determinism.
