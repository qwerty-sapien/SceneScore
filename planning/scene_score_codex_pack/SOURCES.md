# Primary references and verification status

Checked on 2026-09-11. These are implementation references, not evidence that this application's detector, music or animations have been tested. Pin and verify the versions actually installed on the owner's Mac.

## Agent instructions and tools
- OpenAI, project instructions: `https://developers.openai.com/codex/guides/agents-md` (redirects to official ChatGPT Learn). Supports root/nested AGENTS instructions and a concise reading hierarchy.
- OpenAI, skills: `https://developers.openai.com/codex/skills`. Documents repository `.agents/skills` discovery and SKILL.md metadata.
- MCP tools: `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`. Schema-based discovery/invocation. A registry still needs application-specific semantics and permissions.
- OpenAI structured outputs: `https://developers.openai.com/api/docs/guides/structured-outputs`. Schema conformance must be supplemented by local semantic checks and error handling.
- OpenAI billing: `https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform`. ChatGPT and application API billing are separate; confirm the hackathon's supplied API credentials/access independently.

## Muse and evaluation
- BrainFlow supported boards: `https://brainflow.readthedocs.io/en/stable/SupportedBoards.html`. Describes Muse board variants and Mac Bluetooth/platform considerations. The actual headset model must be verified; this is not a claim that this user's device has been connected.
- MNE ocular event detection: `https://mne.tools/stable/generated/mne.preprocessing.find_eog_events.html`. Describes detecting ocular artifacts, including use of suitable EEG channels near the eyes. Its offline helper is not automatically a causal live detector.
- scikit-learn semi-supervised learning: `https://scikit-learn.org/stable/modules/semi_supervised.html`. Unlabelled-data methods rely on assumptions; self-training uses confidence-based pseudo-labelling.
- scikit-learn grouped validation: `https://scikit-learn.org/stable/modules/cross_validation.html`. Grouped splits avoid placing the same group in training and test. Sessions/refits are the relevant groups in this proposal.
- scikit-learn metrics: `https://scikit-learn.org/stable/modules/model_evaluation.html`. ROC and precision/recall metrics are supplementary to the proposed complete-stream gesture metrics.
- SciPy binomial intervals: `https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html`. The confidence examples in the brief are explicit binomial/Poisson calculations, conditional on their stated assumptions, not measured Muse results.
- Optuna multi-objective search: `https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/002_multi_objective.html`. A tool for bounded parameter search; no automatic guarantee of accuracy or musical quality.

## Audio and Blender
- W3C Web Audio: `https://www.w3.org/TR/webaudio-1.1/`. Describes scheduled audio sources, routing and parameter automation. The retrieved 1.1 document is a working draft; use browser-supported features and verify actual output timing.
- music21 MIDI translation: `https://music21.org/music21docs/moduleReference/moduleMidiTranslate.html`. Symbolic note/stream and MIDI conversion support, not an audio synthesizer.
- Blender dependency graph: `https://docs.blender.org/api/current/bpy.types.Depsgraph.html`.
- Blender CLI: `https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html`.
  The Blender pages could not be fetched in this research environment. The prompts explicitly require installed-version inspection and local render/export tests. Their presence in this list is a verification task, not a claim of successful retrieval.

## Private-repository limitation
Connected GitHub searches for RAGTM and related names did not locate the user's prior project. The lineage prompt requires an actual local path or accessible repository and forbids invented baseline details. No unrelated public repository has been treated as RAGTM.

## Creative provenance
All four composition motifs, three brush recipes and ten animation briefs in `seeds/` are newly authored design specifications in this pack. No finished audio, third-party recording, trained model or rendered animation is included. Musical originality in the broader historical sense has not been established; familiar harmony and instrument techniques are intentionally used.
