# Export, handoff and Foley boundary review

Date: 2026-09-13. Scope: source review and read-only inspection of the current
`artifacts/blender/revamp/review/05_bouncing_staircase-32` candidate. The reviewer
authored the exporter/handoff changes earlier in this DAG; this is an additional
boundary audit, not independent-author node 08 approval. It is not human approval,
audio audition, continuous-motion perception or a claim that the integrated
product has passed.

## Findings and minimal repairs

### Sampled contact-envelope entry does not establish impact time

The inspected candidate contains 16 canonical interactions: 11 contact onsets,
four near misses and one supported contact release. Eight of the onsets have
independently fitted between-sample contact certificates. The other three are
sampled distance-envelope entries: initial ramp settling and two back-stop
episodes. They were marked geometry-validated but not `physical_impact`; that
distinction was lost at the original preparation allowlist, which selected every
validated canonical contact onset for Foley.

The envelope events remain useful canonical geometry records. Under the user's
requirement for Foley from validated physical contact episodes, their positive-gap
entry time alone is insufficient to certify a physical impact cue or its timing.
In particular, the one-tick sampling uncertainty describes detection of the
envelope entry, not uncertainty of the true physical collision time.

A separate closest-point sphere/OBB calculation, written for this inspection
without importing exporter or validator collision functions, measured:

| Sampled-only onset | Onset (s) | Raw gap at onset (m) | Envelope (m) | First later sampled gap <= 10 micrometres |
| --- | ---: | ---: | ---: | --- |
| Ramp | 0.0583333333 | 0.00074002215 | 0.0022 | 0.0708333333 s, 12.5 ms later |
| First back-stop | 4.2500000000 | 0.00030792236 | 0.0034 | None within the following 120 ms |
| Second back-stop | 4.5583333333 | 0.00303209305 | 0.0034 | 4.6000000000 s, 41.667 ms later |

These later near-zero samples are not independently certified impact times.
Absence of a near-zero sampled gap does not prove absence of an intersample
collision. The measurements establish the narrower timing ambiguity above.

The authorized source repair preserves those canonical geometry records and adds:

- `time_semantics: sampled_envelope_entry` for sampled contact onsets;
- null `physical_impact_time_s` and `physical_impact_time_uncertainty_s`, with a
  reason explaining that sampled geometry cannot establish impact time;
- `foley_eligible: false` and a reason on uncertified geometry records;
- `foley_eligible: true` only on independently certified contact onsets. A
  supported-release certificate is not a Foley onset and remains ineligible.

The coordinator owns the preparation filter, which must require both `validated`
and `foley_eligible`. This intentionally yields the eight certified contact cues
for this candidate after regeneration. It does not claim complete collision
coverage and does not reclassify either back-stop episode as a proven miss.

### A static supported state is not a settling event

The inspected handoff contained eight contact markers, one supported release and
two settling markers. The dynamic ball's final low-motion window is meaningful
under its declared endpoint-support scope. The passive step's all-scene rest
window produced an inappropriate settling marker at time zero.

The source repair emits settling markers only for `mode: dynamic` objects, both
for explicit supported-rest validation cases and for fallback rest metrics.
Passive and driven support states remain in the evidence; they do not become
settling events. Explicit nondynamic supported-rest cases receive an unavailable
marker reason. The dynamic marker still says that it identifies the start of a
verified rest window, not an independently localized first settling time.

### Handoff and feature bytes must be bound through selection and approval inputs

The inspected pre-staging bundle index contains the contact-certificate supplement
and other physics/source inputs. The separately written handoff index correctly
contains `handoff.json` and `features.jsonl`, but those files are not yet present
in the candidate's original bundle index. The coordinator's staging implementation
is responsible for verifying and adding the handoff index and members before
sealing the chosen bundle. Unstaged candidate output is not proof of selection
integrity.

At the start of this audit, preparation attached the handoff after constructing
the arrangement Context, so a handoff/features-only change did not affect the
plan's scene input hash. This was reported immediately. The coordinator has since
added a `scene-music-input-binding-1` object with exact handoff, feature and index
hashes to the Context and preparation path. Browser-side input verification and
approval invalidation tests remain coordinator/integration-owner work; this
review does not assert they have passed.

Recommended sealing check: require both `handoff.json` and `features.jsonl` as
members of the handoff index, and verify `handoff.features.sha256` against the
actual feature bytes. Iterating only whatever members happen to be present in an
index is weaker than enforcing these required members. No corrupted actual index
was observed.

## Scope of existing certificates and roles

The eight fitted contact markers carry one-tick uncertainty, later fit-window
confirmation, exact source/report references and normal-response-only scope.
They do not claim a measured physical impulse or complete collision coverage.
The report has 20 unverified contact intervals, two unverified release transitions
and 44 velocity-discontinuity intervals; these must not silently become cues.

The supported-release marker is at 1.145446079548219 s, with confirmation at
1.1791666666666667 s. Its scope is a prior finite-face support episode followed
by separated gravity flight with fitted position/velocity continuity. It does
not certify launcher impulse or an expected launch-velocity calibration.

The ball's final low-motion window begins at 7.754166666666666 s and is confirmed
at 8 s. Its support check is at the endpoint. This is an honest window marker,
not proof that this is the first instant of settling.

Scored identities in this candidate include the ball and the four explicitly
scored steps. Passive mode alone does not make an object silent. Floor, ramp,
rails, legs and back-stop are silent supports. A read-only arrangement compile
retained those five scored motif owners and did not assign motifs to silent
supports. Before the eligibility repair, that compile produced 200 notes,
96 brush events and 11 Foley cues, at the existing canonical onset times.

## Validation and artifact boundary

Focused source tests after the minimal repair:

```sh
cd /private/tmp/scenescore-revamp-tooling
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/blender/tests/test_production_export.py modules/blender/tests/test_music_handoff.py -q
/Users/agent/Desktop/SceneScore/.venv/bin/python -m ruff check modules/blender/production/export.py modules/blender/production/handoff.py modules/blender/tests/test_production_export.py modules/blender/tests/test_music_handoff.py
git diff --check
```

Results: 40 tests passed in 0.99 s; Ruff passed; diff check passed. Tests exercise
positive-gap sampled onset semantics, conservative Foley eligibility, certified
onset/release separation, and passive/driven rest suppression while retaining
dynamic settling. This worktree's production files are untracked, so the diff
check alone does not validate their content; the named test/lint checks do.

No candidate was regenerated after the coordinator requested this boundary
review. No Blender process was launched. The read-only in-memory arrangement
compile exited with code zero; its exec session was 20222. There are no owned
persistent jobs from this review.

After copying the source repair, the coordinator must regenerate the candidate
export/handoff, seal the bundle, verify eight eligible Foley cues and removal of
the passive settling marker, and run preparation/browser hash and approval
invalidation tests. Exact rendering, playback, mix/stem alignment and human
approval gates are not satisfied by these unit tests.

## Inspected artifact hashes (pre-repair snapshot)

These hashes identify the bytes inspected before source repairs. They do not
describe a regenerated delivery or supersede later coordinator sealing.

| File in the review candidate | SHA-256 |
| --- | --- |
| `production.json` | `921d18fdf190ef17b0fa1c9f039a92bd4e12555b636719919ec5848b0cd9da80` |
| `manifest.json` | `8009edda43db7ddeb4f9310795c06e72067ad826e9a2c9482eb2dc741bf0452d` |
| `geometry.json` | `7b0a59fa7a1caa8326b31df755c19d63bc0a603be560b06fa1f816f1213d72f0` |
| `interactions.jsonl` | `b059ca8bb53a8ad9ec6502af39763e92d1111ba4d1eda0f3cf7d75e20b5e426a` |
| `contact_intervals.json` | `7c3af9ee0cc913817a40cb32a5a51a3fa586e9a7f5b1b6c12075e478ee187125` |
| `handoff.json` | `6274f9a37b776c96db47b89f9b5c2dd475cf63e1c1d8fb7ec001a9f19acbfd28` |
| `features.jsonl` | `3454090447b30a25bcb2ab90b6ffa9fa7c4ce7d8075e83ff06ab621ebf7a4ffd` |
| `handoff_hashes.json` | `fe063978b117373e51f3e525de9ff8eac79f397db94208445c86b1e47c1bba9f` |
| `bundle_hashes.json` | `57acd33c5670e50c7267cfc78336c0fdffa79f0a31b9412b1bf51b956997a5d5` |

Primary implementation hashes captured during the read-only review, before the
latest minimal repair and subject to concurrent coordinator changes:

| File | SHA-256 |
| --- | --- |
| `modules/blender/production/export.py` | `1546b57dcbb2daa2526324d395527844c430a4d0ee4e1e31359cd8172c2bc86e` |
| `modules/blender/production/handoff.py` | `08194fa8f0b59a2422306df526147f7e3f07550f59fc898444dc8489ad72213e` |
| `modules/blender/production/contact_intervals.py` | `bf25a56a441fa2461cec37bd7a187990b3fd493246f324a5b56eef711b1dfa7e` |
| `modules/blender/production/staging.py` | `22298777e09d81fc9c7151f5b4f6689c601661bad2595b1a27f259ff4c942041` |
| `modules/blender/selection.py` | `6d78e0f75fdcce37677e286a994b6674cffcc89b846d91c4c2c9eb10c6e4b7ed` |
