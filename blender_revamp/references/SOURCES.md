# Primary references and evidence provenance

Checked on 2026-09-12. Recheck live documentation when executing the pack. These links support tooling/physics concepts; they do not certify the proposed implementation.

## MCP integration

- Upstream requested integration: https://github.com/ahujasid/blender-mcp
- Its README documents a Blender addon plus MCP server, code execution and inspection, Codex setup, loopback connection defaults, optional safe mode and telemetry opt-out. The pack additionally requires local isolation, pinned compatible revisions, minimal permissions and reproducible changes. These additional requirements are design decisions.
- OpenAI's MCP documentation: https://developers.openai.com/codex/mcp (redirects to the current ChatGPT Learn MCP documentation). It documents local STDIO servers, project-scoped trusted `.codex/config.toml`, environment settings, tool restrictions and timeouts. The pack avoids changing global settings.

## Mechanics

- OpenStax, University Physics Volume 1, section 4.3: https://openstax.org/books/university-physics-volume-1/pages/4-3-projectile-motion
- OpenStax, University Physics Volume 1, section 9.4: https://openstax.org/books/university-physics-volume-1/pages/9-4-types-of-collisions

The analytical fixtures apply elementary uniform-gravity and isolated collision models with explicit assumptions. Their numerical values are calculated for this pack and are not copied simulation results. Real solver tolerances and effective material response need local calibration.

## Blender documentation to verify locally

- Command-line rendering: https://docs.blender.org/manual/en/latest/advanced/command_line/render.html
- Command-line arguments: https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html
- Rigid-body world: https://docs.blender.org/manual/en/latest/physics/rigid_body/world.html
- Rigid-body tips: https://docs.blender.org/manual/en/latest/physics/rigid_body/tips.html
- Collision properties: https://docs.blender.org/manual/en/latest/physics/rigid_body/properties/collisions.html

Direct retrieval of these Blender manual pages failed in this session, including alternate versioned URLs. An indexed official command-line excerpt confirmed that argument order matters, but it was insufficient to verify current detailed API behavior. The pack therefore requires the agent to consult accessible version-matched official documentation and introspect the actual installed Blender RNA/API. It deliberately does not prescribe unverified properties for rigid-body initial velocity, caches or layered actions.

## Local evidence

See `BASELINE_AUDIT.md` for exact snapshot paths. `evidence/baseline_metrics.json` records hashes of key inspected source files and sidecars. `evidence/recompute_baseline.py` independently recomputes sampled axis-aligned cube overlap from supplied evaluated bounds. The original video hash matches its counterpart in the uploaded archive.

The generated pack supplies instructions, reference data and extracted evidence. It does not contain a newly simulated/re-rendered Blender solution or claim a successful MCP connection.
