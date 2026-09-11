# RAGTM lineage — source inspected, runtime unverified

User supplied `/Users/agent/Downloads/RageAgainstTheMachine-main.zip` during Phase 0 and explicitly requested establishment on Desktop. Extracted unchanged to `/Users/agent/Desktop/SceneScore/RageAgainstTheMachine-main`; all 802 regular files byte-verified against the ZIP. This external source snapshot is SceneScore's documented `RAGTM_PATH`; no game code has been imported into SceneScore. The environment variable itself is not globally set. Prior `RAGTM_NOT_INSPECTED` condition is superseded by this bounded source audit.

Archive comment identifies `8258b4edddd35c301959bf0ab24e2305938579af`. This is an archive-reported commit identifier, not a verified Git HEAD: the ZIP contains no `.git` history. No Git initialization, dependency installation, server launch, hardware recording or baseline benchmark was performed. Source instructions were read as repository context; its game/stress goals do not override SceneScore's VISION. Preserve the ZIP and snapshot unchanged for later comparison.

## Exact inspected paths (relative to the Desktop snapshot)
| Path | Evidence / implications |
|---|---|
| `AGENTS.md` | React/Vite, Python/FastAPI, BrainFlow/LSL context. Its game/opponent instructions are not SceneScore requirements. |
| `frontend/src/hooks/useBCIStream.ts:26` | Defaults: EMA alpha .02, cooldown 250ms, score threshold 4, minimum amplitude 50µV, deviation floor 7µV, one-second warmup; configurable and stored per device. These are observed source defaults, NOT adopted calibrated SceneScore values. |
| `frontend/src/hooks/useBCIStream.ts:339` | Uses absolute filtered amplitude against adaptive mean/absolute-deviation proxy; requires selected channels, warmup and cooldown. Frontal channels selected when available. The so-called z-score is not evidence of calibrated probability. Quality values are computed but the inspected blink condition does not explicitly gate on railed status. |
| `frontend/src/hooks/useBCIStream.ts:276` | Timestamp uses payload column 1 with Date.now fallback; accumulated display time advances by sample count/rate. Requires explicit clock/gap handling in an adapter. |
| `frontend/src/pages/FlappyBirdPage.tsx:693` | Positive blink-count delta invokes flap once per observed effect in running EEG mode. A delta greater than one can be coalesced into one flap. This supports a code path, not the user-reported success rate. Decorative power/hemisphere/confidence values are generated here; they are not raw EEG or calibrated evidence and must not transfer. |
| `backend/eeg/services/muse_stream_service.py:27` | Selects muse_v1 registry config and reads existing LSL chunks. No actual connected device verification in this audit. |
| `backend/eeg/services/muse_stream_service.py:164` | Five-second rolling buffer/warmup; detrend, 50Hz environmental-noise removal and 1–50Hz order-2 Butterworth. Re-filtering a buffer needs causal/chunk-boundary characterization; do not assume equivalence to a stateful streaming filter. |
| `backend/eeg/services/muse_stream_service.py:240` | Treats LSL timestamps as Unix timestamps for formatting. Clock semantics require explicit verification before reuse; no inferred wall-clock alignment. |
| `backend/eeg/services/streaming/device_registry.py` | Declares Muse v1, TP9/AF7/AF8/TP10, 256Hz and µV-related range. This is configuration evidence, not proof of the owner's headset generation/units/rate. |
| `backend/eeg/services/streaming/session_manager.py` | CSV sessions under data/raw/eeg; raw rows appended by acquisition. Independent labels, clock metadata and deterministic replay still need design. No validated replay command established by the bounded audit. |
| `backend/eeg/services/muse_stream_service.py:295` | On exit, optional HF_REPO_ID triggers upload. Do not run the old capture blindly; Phase 2A must enforce offline/scoped execution and no uploads, without editing this snapshot. |
| `backend/pyproject.toml` | Requires Python ≥3.12 and a broad stack including BrainFlow ≥5.19, pylsl ≥1.18.1, NumPy, FastAPI and many unrelated ML/vision packages. Compatibility with observed Python 3.14.6 is unverified; do not install wholesale. |
| `LICENSE`, `.gitmodules` | Root MIT notice (2026 AETHER by RAiD) requires retention with copied substantial code. External submodules have separate sources/terms; no blanket clearance asserted for them, models or recordings. |

## Reuse plan and boundary
Phase 2A may build a scoped adapter in `modules/muse/baseline/` around the observed deterministic candidate logic and acquisition format, preserving attribution and all original parameter/clock assumptions. Emit candidate IDs/times/scores into canonical contracts; a separate SceneScore grammar decides deliberate doubles and rejects singles/ambiguous trains. Do not translate single blink directly to modulation or reuse synthetic game telemetry.

Maintain two distinguishable comparators: unchanged source baseline (runtime/replay feasibility pending) and any extracted/ported adapter (new version with equivalence tests). Compare identical genuine held-out sessions; record code/config/data hashes and behavior differences. Baseline cannot currently be called runnable or validated. Some `.pth` entries are Git LFS pointer files, so the source archive does not establish availability of model weights. Existing recordings are not automatically independently labelled consented SceneScore test data. No training or data reuse is authorized by this source audit.

## Desktop establishment correction

At the user's correction, the unchanged source snapshot was moved beneath the greenfield Desktop/SceneScore root and initialized as an independent local Git repository. No source commit, remote, upload, dependency installation or application execution was performed. Earlier statements that the ZIP has no Git history remain true; the new local repository is unborn. Parent Git ignores this child repository.
