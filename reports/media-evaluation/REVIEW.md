# Preregistered sampled media review

Status: **COMPLETED_WITH_MODALITY_LIMITS**

Repository revision inspected: `682f40b79f0a57825a2d69b63b5c43bf52e4b1e5`

Frozen sample: 4/17 distinct units = **23.53%**, seed `7811544884403853071`

Release effect: **none**. Music and arranger artifacts remain `AUDITION_PENDING`; the formal project gate remains open.

## Result

All four frozen selected hashes match `sample.json`, the protocol hash matches, all 283 hash-indexed supporting files match their local indexes, and all four selected media files decode successfully. These are byte-integrity and technical-decode results. They do not establish music quality, full-motion quality, physical synchronization, or approval.

The sampled near-miss scene has coherent objective sidecars: three approach, three near-miss and three separation events over three pairs; minimum reported gap 0.5 m versus 0.00001 m uncertainty; negative approach speeds, positive separation speeds, zero contact events and no physical-impact claim. Four labelled stills and a 12-frame contact sheet visibly show the projectile traverse left-to-right and separate from the tower. One projected view overlaps the lower tower area, so pixels alone do not establish the physical gap; the sidecars carry that claim.

One concrete supporting-document defect was found. `artifacts/music/review-v2/velvet_orbit_v1/sparse/lead-sheet.md` line 6 says “The straight rag remains straight,” although the artifact uses the sparse-ballad groove and is not the straight-rag composition. The authoritative JSON remains explicit, but the human-readable style description is misleading.

No audio-perception tool was available or used. I did not hear the three WAV files. I did not watch the complete video in continuous motion. Human musical phrasing, chord-transition perception, balance, clicks, ending/loop feel, timbral realism, Foley sound, bossa/swing feel and expressive performance remain unscored. Physical browser/audio/display timing and real Muse behavior also remain untested.

## Per-unit findings

| Selected unit | Objective checks | Symbolic, geometry or visible evidence | Defects and limits | Status |
|---|---|---|---|---|
| `corner_pocket_rag_v1/base/mix.wav` (`ec0d836f…679c`) | **Evidence-supported pass.** PCM16LE mono, 48 kHz, 16.35 s, peak 0.126190, RMS 0.021204, 0 clipped samples, nonzero signal, zero first/last sample. | **Evidence-supported pass, symbolic only.** Eight bars, 4/4 at 120 BPM; straight-rag ratio 0.5; explicit harmony, loop, five control lanes and rests; 160 events; 12 object-motif events in one bounded lane. | Scene response **not applicable**. Heard form/style, cross-loop/key-change identity, originality/similarity, rights and performance **not assessable**. | `AUDITION_PENDING` |
| `velvet_orbit_v1/sparse/mix.wav` (`cb5d08d3…aa9`) | **Evidence-supported pass.** PCM16LE mono, 48 kHz, 24.35 s, peak 0.095764, RMS 0.010792, 0 clipped samples, nonzero signal, zero first/last sample. | **Evidence-supported pass, symbolic only.** Eight bars, 4/4 at 80 BPM in D minor; explicit extended harmony, loop, five control lanes and rests; 80 events; 6 object-motif events in one bounded lane. | **Evidenced defect:** incorrect straight-rag sentence in its lead sheet. Scene response **not applicable**. Heard lyrical/bossa/swing character, cross-loop/key-change identity, originality/similarity, rights and performance **not assessable**. | `AUDITION_PENDING` |
| `10_projectile_tower-near_miss/preview.mp4` (`bd5699cf…27f8d`) | **Evidence-supported pass.** H.264, 320×180, 8 fps, 30.0 s, 240/240 frames; ffmpeg decode passed; parent validation reports frame/duration/hash, evaluated trajectory and continuous near-miss certificate passed. | **Evidence-supported pass.** Positive-gap approach/near-miss/separation semantics; four stable object/sonic IDs. Bounded visible observation from four labelled stills and the contact sheet shows approach and separation. | Physical dynamics were not simulated; scripted analytic sphere/AABB proxy. Foley **not applicable** because the video has no audio stream. Full-motion smoothness and physical AV sync **not assessable**. | `VISUAL_REVIEW_BOUNDED`; full motion not assessed |
| `evaluated-hero-audition/baseline.wav` (`09128b43…9293`) | **Evidence-supported pass.** PCM16LE mono, 48 kHz, 30.35 s, peak 0.164642, RMS 0.026516, 0 clipped samples, nonzero signal, zero first/last sample. | **Evidence-supported pass, symbolic only.** Draft manual plan; 308 events and 12 lanes; four motif owners with three active object voices; causal world-Z mapping with 0.3 s lookback, 0.02 m/s deadband and prepared −2/+2 semitone transitions. | Contact Foley **not assessable** in this WAV: it is explicitly excluded, and the 12 exact-scene-time Foley records are only a separate schedule. Near miss **not applicable** to its contact-scene context. Heard arrangement, paired video and physical sync **not assessable**. | `AUDITION_PENDING`; no approval object |

The full structured criterion records, exact hashes and raw facts are in `metrics.json`.

## Position-bias adaptation

The procedure adapts Shi et al., [Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge](https://aclanthology.org/2025.ijcnlp-long.18.pdf), Sections 2.1–2.2. Candidate titles, variation labels, source paths, content hashes, prior reports, approval/audition labels and the private identity mapping were removed before trials. Duration, tempo, harmony, density and scene structure remain possible identity clues. The controls were byte/evidence duplicates; a judge could recognize equality from their records.

Six independent fresh contexts were created in three waves of at most two: three received the original packet and three received the swapped packet. Every context judged the same music, visual and arranger tasks. All six were requested/configured as `gpt-5.6-sol`, reasoning effort `xhigh`. The orchestration interface accepted those settings; it did not expose an additional runtime model fingerprint. Each trial recorded the expected packet hash and valid JSON output. No judge read another trial or the private mapping.

Original and swapped trials were paired by repetition index. `C` means tie. `NOT_ASSESSABLE` was allowed and would have been excluded; none of the three overall pair tasks required it because each had comparable technical/symbolic evidence, although individual perceptual criteria remain not assessable.

| Scope | Valid pairs N | Raw choice pairs | RS | PC | pcn / rcn | PF_raw | PF | Meaning |
|---|---:|---|---:|---:|---:|---:|---:|---|
| Substantive music evidence pair | 3 | `AB=3` | 1.000 | 1.000 | 0 / 0 | 0 | 0.000 | Same underlying unit selected after swap; technical/symbolic evidence only |
| Exact-duplicate controls | 6 | `CC=6` | 1.000 | 1.000 | 0 / 0 | 0 | 0.000 | Tie consistency only; no media-quality content |
| Combined descriptive total | 9 | `AB=3, CC=6` | 1.000 | 1.000 | 0 / 0 | 0 | 0.000 | Descriptive aggregate only |

`ipr` and `irr` are undefined because there were zero inconsistent pairs; per protocol, `PF_raw` is then defined as zero. PF uses the preregistered attainable bounds −N/+N, so `PF = PF_raw/N`.

All three original-order judges chose the first music candidate and all three swapped-order judges chose the second, mapping to `corner_pocket_rag_v1/base` in both orders. Their reasons emphasized greater evidence volume: 160 versus 80 resolved events and 12 versus 6 object-motif events. The comparison deliberately hid the `sparse` variation label, so density is confounded with the second work’s intended sparse design. This stable result is not an auditory or artistic ranking.

RS/PC/PF are therefore valid descriptive results for these packet tasks only. Three substantive pairs and six duplicate controls cannot certify judge unbiasedness, a music-quality instrument, any sampled artifact’s artistic merit, or the 17-unit catalogue. The stratified 4/17 allocation is not self-weighting, so no catalogue success rate is reported. This is pairwise only; no listwise experiment or replication of Shi et al.’s text benchmarks is claimed.

## Evidence and provenance

- `sample.json`: immutable universe/sample, seed and selected hashes.
- `source-checks.json`: 4/4 selected hashes, protocol hash, 283 indexed supporting hashes, ffprobe records and ffmpeg decode results.
- `provenance.json`: private packet mapping, packet hashes and blinding limits.
- `packet_alpha.json`, `packet_beta.json`: frozen neutral original/swapped evidence.
- `trials/alpha-{1,2,3}.json`, `trials/beta-{1,2,3}.json`: six independent raw judge records.
- `metrics.json`: full unit findings, raw pairs, counts and formulas.
- `artifacts/media-evaluation/neutral/stills/`: four neutralized copied stills.
- `artifacts/media-evaluation/analysis/scene-contact-sheet.png`: 12 sampled frames used for bounded visual inspection, SHA-256 `56200eb9…f5929`.

The neutral packet extractor records that coordinator-produced statistics are not independent recomputations by the judges. Arranger supporting JSON lacks a frozen support index; its observed hashes are provenance only. Music and scene supporting files were checked against their provided local indexes.

## Commands and tool actions actually run

- `shasum -a 256` on the four selected units and `PROTOCOL.md`: all matched `sample.json`.
- `.venv/bin/python reports/media-evaluation/extract_neutral_packet.py`: verified the frozen inputs and wrote alpha/beta packets plus coordinator provenance; final packet hashes `f30034eb…f58d` and `6fee6a8b…afa4`.
- `.venv/bin/python reports/media-evaluation/verify_sources.py`: **PASS** for selected hashes, protocol hash, 283 indexed supporting hashes and all four ffmpeg decodes.
- `ffprobe` on all four selected files: PCM/audio and H.264 metadata reported above.
- `ffmpeg -v error -nostdin -i …/preview.mp4 -f null -`: exit 0.
- `ffmpeg … -vf "fps=1/2.5,scale=320:180,tile=4x3" …/scene-contact-sheet.png`: exit 0; analysis-only frame extraction, not source-media generation.
- `view_image` on `start.png`, `approach.png`, `event.png`, `ending.png`, and the 12-frame contact sheet: bounded visual observations reported above.
- `jq`/`sed` inspection of music manifests, scores, resolved events, brush recipes and lead sheets; Blender manifest, geometry, interactions, QA and validation; arranger input, plan, baseline and Foley event schedules.
- Six fresh judge contexts via the orchestration tool: all completed and wrote one owned trial JSON each.
- `.venv/bin/python reports/media-evaluation/compute_metrics.py`: `RS=1.0`, `PC=1.0`, `PF=0.0`, N=9, `AB=3`, `CC=6`.
- `.venv/bin/ruff check` on `extract_neutral_packet.py`, `verify_sources.py` and `compute_metrics.py`: all passed.
- Final `jq -e` assertions over `metrics.json` and all six trials: passed.

No application code, source media, models or approvals were changed. No training, application/provider API call, playback server, browser, container, watcher or other persistent job was started by this evaluation. The ACL paper was read from its primary web PDF, and the six explicitly authorized judge contexts were the only model-evaluation calls. All shell analysis commands exited; no task-owned residual job exists.

## Open gates

- Genuine human audition of every exact music/arranger hash and exact-plan approval.
- Continuous full-motion visual review.
- Audible contact Foley and integrated near-miss soundtrack review.
- Physical/target-browser audio/display timing capture.
- Real Muse sessions with independent labels and the Phase 3A empirical gates.
