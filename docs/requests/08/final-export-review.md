# Final export review

2026-09-13. Bounded read-only review of the three regenerated browser exports and their final muxes. Current delivery audit returned `PASSED`. This establishes bytes, clocks, PCM alignment and certified-contact correspondence. It does not establish human approval, audio audition, continuous-motion perception, hero completion or complete catalogue delivery. The delivery remains `PARTIAL_BLOCKED_HERO`; all checked exports and muxes carry `approval: null`.

## Result

The three final bundles have distinct IDs and preserve 304 swing, 244 ballad and 280 rag source events. Each contains eight Foley cues at exact certified-contact marker times. The audit checked all five WAV files per bundle, original event preservation, playback projection, exact selection identity, PCM stem summation, final-sample silence and ten marker-to-frame references. All five WAVs per bundle are stereo 16-bit PCM at 48 kHz with 384000 frames: 8 seconds and 1600 samples per each of 240 delivered video frames.

For each final mux, the actual mux bytes match its report hash, the report's source-report hash matches the exact corresponding final browser report, and the selection/playback-window bindings match. The saved mux jobs report successful exits and absent process groups. No new decoder, renderer or browser was launched by this review. The coordinator's separate `final-mux-decoding.json` records full decoding, 240 video frames, 384000 audio samples and zero initial PTS for each final mux; that stored evidence was inspected, not independently rerun here.

## Scope of current mux checks

Source inspection confirms `verify_export` requires production selections to include a playback policy and window; requires policy equality to the window's version, start, duration, fps and final fade; binds policy, roles and music-handoff binding to hashed scene-input bytes; verifies exact window and original-event bytes; independently reconstructs the projection; and requires 48 kHz PCM with frame_count * 1600 samples. Existing legacy exports without this supplement remain supported, while draft exports must carry null approval.

The review did not mutate candidate, report, WAV or mux files. All 25 tracked input artifacts were byte-identical before and after the checks. The delivery-index hashes that were present matched their corresponding actual files. The exact staircase selection was correctly bound through all three export reports and the audit; the list below records any selection/index omission observed while the coordinator was still finalizing the index. An empty list means it was already resolved.

## Invalidated evidence stays separate

`reports/blender-revamp/export-invalidation.json` describes the prior shared Playwright listener overwrites. The old `reports/blender-revamp/delivery-audit.json` and `artifacts/blender/revamp/integration/staircase-DRAFT.mp4`, `staircase-ballad-DRAFT.mp4`, `staircase-rag-DRAFT.mp4` are superseded and are not accepted by this review. Only `output/playwright/blender-revamp/final-exports/*/scenescore-DRAFT.json` and `artifacts/blender/revamp/integration/final/*-DRAFT.mp4` below were checked as final output. The stored final audit is `reports/blender-revamp/delivery-audit-final.json`. Preserved earlier browser timing evidence was not recreated or upgraded into new verification.

## Commands and checks

Ran the current audit function in memory from the primary repository with the primary interpreter:

```sh
PYTHONPATH=src /Users/agent/Desktop/SceneScore/.venv/bin/python - <<'PY'
from pathlib import Path
from tools.audit_blender_delivery import audit
root = Path.cwd()
selection = root / 'artifacts/blender/revamp/review/staircase-selection.json'
base = root / 'output/playwright/blender-revamp/final-exports'
reports = [base / groove / 'scenescore-DRAFT.json' for groove in
           ('brush_swing_light_v1', 'brush_ballad_sparse_v1', 'brush_straight_rag_v1')]
result = audit(selection, reports)
assert result['status'] == 'PASSED'
print(result['status'], len(result['exports']), len(result['marker_frames']))
PY
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest tests/test_playback_mux.py tests/test_phase3.py -q
```

The actual read-only audit wrapper additionally asserted expected event counts, distinct IDs, all individual file hashes, mux source-report and selection/window equality, null approvals, recorded mux job cleanup, unchanged tracked inputs and matching delivery-index hashes. Exact measurements are below. The focused playback and legacy tests passed: **10 passed in 0.72 s**, with two existing Starlette/httpx deprecation warnings. Two preliminary wrapper attempts stopped after audit completion on review-script assumptions (a `.mux.mp4` filename and treating the selection as an existing flat-index member); the corrected wrapper completed. These were inspection-script errors and made no artifact changes.

## Exact final evidence

```json
{
  "status": "PASSED",
  "selection": {
    "selection_file": "/Users/agent/Desktop/SceneScore/artifacts/blender/revamp/review/staircase-selection.json",
    "selection_sha256": "5e51110a180eeaf7912cf4be11b8f5d0e469a0d25b0522d936d8e892bfc9886d",
    "variant": "05_bouncing_staircase",
    "entry": {
      "bundle_index_hash": "760d30c8198be56067bd8afaf2ef6cfe3369971084f829573cac4b6a5c99cc80",
      "media_validation_hash": "7b08a3fc7e749dfd6ca683242d1f5d224fa601476fe7a6b713111ba57e4464ac",
      "media_validation_path": "renders/preview/beauty/media-validation.json",
      "music_handoff_hash": "22fdfbffeee682607ad447a09bdc372ec80f981c6ae961a16c105681ec628712",
      "path": "revamp/review/05_bouncing_staircase-32",
      "physical_validation_hash": "70bbd227a476c5d26d7ed0a0e673d349bdb920ac55ff34ff87df4cbefe8b2253",
      "roles_hash": "6693da608f36a6f81d982e4546156ab8a8eafb59643b4c2b5bea6e73d6f562be",
      "scene_id": "05_bouncing_staircase:default:c5ee061e06e8074c",
      "source_hash": "854e00a2410ceab0aab690207a4649ad9c66c1255f7567cd954988ede1c6a30d",
      "video_hash": "4dda38d936d12b2948faf77712cd8767a8cbaae5ed11514f7776dbbf56c8cdc7"
    },
    "legacy_choreography": false,
    "label": "Staged production review \u00b7 acceptance pending",
    "approval": null
  },
  "exports": [
    {
      "variant": "swing",
      "bundle_id": "05_bouncing_staircase-brush_swing_light_v1",
      "event_count": 304,
      "original_event_count": 304,
      "window_events": 95,
      "certified_foley_events": 8,
      "report_path": "output/playwright/blender-revamp/final-exports/brush_swing_light_v1/scenescore-DRAFT.json",
      "report_sha256": "bee88b155ec4e19fbf2a8ce5bc7cee3ecbf087877193dc69673fb96bf4f53226",
      "wav_files": [
        {
          "stem": "mix",
          "filename": "scenescore-DRAFT.wav",
          "sha256": "827b3642561b1c2088bbffee4ed9eb91c20b8bada76c32afa9396d8ffba46d83",
          "measurements": {
            "peak": 0.01843414641916752,
            "rms": 0.0035138819588742447,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "piano",
          "filename": "scenescore-DRAFT-piano.wav",
          "sha256": "bc2f4064f4e0f3df7a8c70d29ae14d77988fc80162754bef51ce92c01f0cefc0",
          "measurements": {
            "peak": 0.01643352396786213,
            "rms": 0.003433383400471608,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "bass",
          "filename": "scenescore-DRAFT-bass.wav",
          "sha256": "fd834fa54757bf8d577083d5b5b2e048a15d26d3cf9a375eac3ddd8b50be493c",
          "measurements": {
            "peak": 0.0032412896398454905,
            "rms": 0.0005042587615394485,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "brush",
          "filename": "scenescore-DRAFT-brush.wav",
          "sha256": "fa53336a80b169ddd703fa3a41c147d18be301107c8f3f85c356ef7f4e87333b",
          "measurements": {
            "peak": 0.0016889401013031602,
            "rms": 0.00030953432026784917,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "foley",
          "filename": "scenescore-DRAFT-foley.wav",
          "sha256": "4750bffa167c8d86025e8c57efd980e79b79ce70f73b2152577266ee43fed9b8",
          "measurements": {
            "peak": 0.002265369985252619,
            "rms": 5.03518137367885e-05,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        }
      ],
      "dimensions": {
        "mix": [
          2,
          2,
          48000,
          384000
        ],
        "piano": [
          2,
          2,
          48000,
          384000
        ],
        "bass": [
          2,
          2,
          48000,
          384000
        ],
        "brush": [
          2,
          2,
          48000,
          384000
        ],
        "foley": [
          2,
          2,
          48000,
          384000
        ]
      },
      "max_stem_sum_error_lsb": 2,
      "rms_stem_sum_error_lsb": 0.5434697553682265,
      "final_samples_lsb": {
        "mix": [
          0,
          0
        ],
        "piano": [
          0,
          0
        ],
        "bass": [
          0,
          0
        ],
        "brush": [
          0,
          0
        ],
        "foley": [
          0,
          0
        ]
      },
      "mux_path": "artifacts/blender/revamp/integration/final/swing-DRAFT.mp4",
      "mux_sha256": "07b7a63dff7b3cde02c85648b88c97ca3070dda148a4106c7e805815fe9f60aa",
      "mux_report_sha256": "8ac955d1707d8d8467569d8322cdcc259db70bdab193eefc21377b98a43770bb",
      "mux_source_report_sha256": "bee88b155ec4e19fbf2a8ce5bc7cee3ecbf087877193dc69673fb96bf4f53226",
      "approval": null
    },
    {
      "variant": "ballad",
      "bundle_id": "05_bouncing_staircase-brush_ballad_sparse_v1",
      "event_count": 244,
      "original_event_count": 244,
      "window_events": 79,
      "certified_foley_events": 8,
      "report_path": "output/playwright/blender-revamp/final-exports/brush_ballad_sparse_v1/scenescore-DRAFT.json",
      "report_sha256": "63f5f68fcf03b7206fb9defa0d3fc7cc5aed30999a13775a5c9ebfa898dcc6eb",
      "wav_files": [
        {
          "stem": "mix",
          "filename": "scenescore-DRAFT.wav",
          "sha256": "e5870ed4add1facd912e746e05bcf1a35b6484f13a47a8bd655164496e14ce42",
          "measurements": {
            "peak": 0.018169354647397995,
            "rms": 0.0035068375376276413,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "piano",
          "filename": "scenescore-DRAFT-piano.wav",
          "sha256": "1e40915911d38d445146ae3965973c6ce73fb833029b4c144f6e7c7fe0fbda3a",
          "measurements": {
            "peak": 0.01643352396786213,
            "rms": 0.003433383399719132,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "bass",
          "filename": "scenescore-DRAFT-bass.wav",
          "sha256": "fd834fa54757bf8d577083d5b5b2e048a15d26d3cf9a375eac3ddd8b50be493c",
          "measurements": {
            "peak": 0.0032412896398454905,
            "rms": 0.0005042587615394485,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "brush",
          "filename": "scenescore-DRAFT-brush.wav",
          "sha256": "4bbd0f7c3f28935230ed759539a8b30e089718184fe67eb22c50a6125550b45b",
          "measurements": {
            "peak": 0.001317304209806025,
            "rms": 0.00025575908055984546,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "foley",
          "filename": "scenescore-DRAFT-foley.wav",
          "sha256": "4750bffa167c8d86025e8c57efd980e79b79ce70f73b2152577266ee43fed9b8",
          "measurements": {
            "peak": 0.002265369985252619,
            "rms": 5.03518137367885e-05,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        }
      ],
      "dimensions": {
        "mix": [
          2,
          2,
          48000,
          384000
        ],
        "piano": [
          2,
          2,
          48000,
          384000
        ],
        "bass": [
          2,
          2,
          48000,
          384000
        ],
        "brush": [
          2,
          2,
          48000,
          384000
        ],
        "foley": [
          2,
          2,
          48000,
          384000
        ]
      },
      "max_stem_sum_error_lsb": 2,
      "rms_stem_sum_error_lsb": 0.5419942919441126,
      "final_samples_lsb": {
        "mix": [
          0,
          0
        ],
        "piano": [
          0,
          0
        ],
        "bass": [
          0,
          0
        ],
        "brush": [
          0,
          0
        ],
        "foley": [
          0,
          0
        ]
      },
      "mux_path": "artifacts/blender/revamp/integration/final/ballad-DRAFT.mp4",
      "mux_sha256": "a446a0d4ca76c729c7de008cf242e1b9cd7092d293d44562771d4f79826dbf14",
      "mux_report_sha256": "20cc098decd41bc6494f5143ebe83a699cf56dfdbcc348e7c1df0571328076d3",
      "mux_source_report_sha256": "63f5f68fcf03b7206fb9defa0d3fc7cc5aed30999a13775a5c9ebfa898dcc6eb",
      "approval": null
    },
    {
      "variant": "rag",
      "bundle_id": "05_bouncing_staircase-brush_straight_rag_v1",
      "event_count": 280,
      "original_event_count": 280,
      "window_events": 89,
      "certified_foley_events": 8,
      "report_path": "output/playwright/blender-revamp/final-exports/brush_straight_rag_v1/scenescore-DRAFT.json",
      "report_sha256": "c03232aeb7c3488be3a088955b1f7ef9221adf77e5d74c80bd5e714dc6169773",
      "wav_files": [
        {
          "stem": "mix",
          "filename": "scenescore-DRAFT.wav",
          "sha256": "159c387975a29160fb5f49ab5cdeadb0aca1a251dddbe8743509868d4a5252c1",
          "measurements": {
            "peak": 0.01839481107890606,
            "rms": 0.0035079196218430982,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "piano",
          "filename": "scenescore-DRAFT-piano.wav",
          "sha256": "f3c63565082f7de1e37f5bd583d8ceccc3af2b1eb9603674722eecd74bcfb095",
          "measurements": {
            "peak": 0.01643352396786213,
            "rms": 0.00343338339947508,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "bass",
          "filename": "scenescore-DRAFT-bass.wav",
          "sha256": "fd834fa54757bf8d577083d5b5b2e048a15d26d3cf9a375eac3ddd8b50be493c",
          "measurements": {
            "peak": 0.0032412896398454905,
            "rms": 0.0005042587615394485,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "brush",
          "filename": "scenescore-DRAFT-brush.wav",
          "sha256": "03887fc9649bc373e1a2a4239d16327c84d2081d8f73b435500967ea4ffc38fd",
          "measurements": {
            "peak": 0.0012877479894086719,
            "rms": 0.0002468086868610889,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        },
        {
          "stem": "foley",
          "filename": "scenescore-DRAFT-foley.wav",
          "sha256": "4750bffa167c8d86025e8c57efd980e79b79ce70f73b2152577266ee43fed9b8",
          "measurements": {
            "peak": 0.002265369985252619,
            "rms": 5.03518137367885e-05,
            "clipped": 0,
            "sample_rate": 48000,
            "duration_s": 8,
            "channels": 2
          }
        }
      ],
      "dimensions": {
        "mix": [
          2,
          2,
          48000,
          384000
        ],
        "piano": [
          2,
          2,
          48000,
          384000
        ],
        "bass": [
          2,
          2,
          48000,
          384000
        ],
        "brush": [
          2,
          2,
          48000,
          384000
        ],
        "foley": [
          2,
          2,
          48000,
          384000
        ]
      },
      "max_stem_sum_error_lsb": 2,
      "rms_stem_sum_error_lsb": 0.5432133366980847,
      "final_samples_lsb": {
        "mix": [
          0,
          0
        ],
        "piano": [
          0,
          0
        ],
        "bass": [
          0,
          0
        ],
        "brush": [
          0,
          0
        ],
        "foley": [
          0,
          0
        ]
      },
      "mux_path": "artifacts/blender/revamp/integration/final/rag-DRAFT.mp4",
      "mux_sha256": "d147b90c9efbf63e7aec5fb16de28a2f621737723b92ed406ae211cbbcbc3a54",
      "mux_report_sha256": "a2209c596fbddd4047215d5b1903d2b9c58e9806ef649f05740c0be65dbb5e15",
      "mux_source_report_sha256": "c03232aeb7c3488be3a088955b1f7ef9221adf77e5d74c80bd5e714dc6169773",
      "approval": null
    }
  ],
  "marker_frames": 10,
  "verified_unchanged_files": 25,
  "delivery_status": "PARTIAL_BLOCKED_HERO",
  "delivery_approval": null,
  "not_in_delivery_index_at_review": [],
  "source_hashes": {
    "tools/audit_blender_delivery.py": "52eb46a0feb241eb810e2ca7e0d0cd4b45e86ddc5ccff2bd259b37e4f10fb39c",
    "tools/mux_performance.py": "740c8600314b008b993c448dd449b11e0f05cb94aed3e20909a34a98fb04e4ac",
    "modules/blender/production/playback.py": "87b351b527c918d9c07e9b927be9a5d73b775e9be3b6ce26f3d827cfc0e5c408",
    "modules/blender/selection.py": "148cbcfb6721634371aa3a1d45b4642fcb7657dee1b9bb7dd8b4684747435b86"
  },
  "invalidation_report_sha256": "ad1aacd3d924511d553c053857447405dfc9485f12a018bce1c382b1e16fb8f3"
}
```
