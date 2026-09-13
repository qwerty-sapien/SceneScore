# Blender physics exemplar search kit

Prepared 13 September 2026. This is a discovery and curation starter kit, not a
prevalidated video dataset or a finished Blender skill. No third-party videos or
project files are included. The seed records have metadata/creator-page checks,
not frame-level event verification. No API credentials are bundled.

## Recommended workflow

Search by mechanism -> inspect creator/source links -> screen a continuous shot
-> obtain an authorized master or render from a licensed project -> annotate
observable events -> create a tested reconstruction -> index by event and solver
family -> retrieve a small diverse set for each new animation request.

Keep discovery candidates, accepted visual references, and reconstruction-tested
examples separate. Do not collapse these into one confidence label.

## Files

- `youtube_queries.txt`: 48 queries in eight mechanism/material families.
- `source_search_queries.txt`: web queries for locating project files and creators.
- `seed_candidates.jsonl`: the three user references plus five additional candidates.
- `collect_youtube.py`: read-only metadata search, channel expansion, and refresh.
- `screening_prompt.txt`: reusable video-screening instructions and JSON output.
- `exemplar_template.json`: a blank, explicitly unreviewed corpus record.
- `clip_commands.txt`: local FFmpeg preparation recipes; no video downloading.
- `few_shot_template.md`: reference-package and generation-prompt conventions.
- `test_collector.py`: offline tests using mocked API responses.
- `SOURCES.md`: documentation and creator-page references.

## No-code starting route

Pick two queries from each of the eight families. Search YouTube normally, then
look for the exact title plus `source file`, `blend`, or `project file` in a web
search engine. A tutorial is useful when it contains a clean final render or a
source project; do not exclude every tutorial at discovery time. Review the
rendered passage, not the screen recording of UI operations.

Treat the query bank as a menu, not a requirement to run all 48 queries. Start
with broad mechanism terms; add rare event words only as a precision pass. The
absence of "near miss" from a title tells you little about whether one occurs.

Once a creator supplies two or more useful candidates, inspect their related
projects and uploads. Prefer this targeted expansion over repeatedly searching
only for "satisfying animation". Broaden creator/style coverage before accepting
many near-duplicates from the same series.

## Programmatic discovery

Use Python 3.10 or later. The collector uses only the standard library. Enable
YouTube Data API v3 for your Google Cloud project and set an API key. Public
metadata access does not require granting access to your personal YouTube account.

```bash
export YOUTUBE_API_KEY="YOUR_KEY"
python collect_youtube.py search --queries youtube_queries.txt \
  --limit-queries 8 --pages 1 --max-results 25 --out candidates.jsonl

# Separate Creative Commons discovery pass; this is not a reuse certification.
python collect_youtube.py search --queries youtube_queries.txt \
  --limit-queries 8 --cc-only --out cc_candidates.jsonl

# Use a UC... channel ID returned in the video metadata, not a @handle.
python collect_youtube.py channel --channel-id "UC_REPLACE_ME" \
  --pages 2 --out creator_candidates.jsonl

# Refresh overwrites old API resources and removes stale details for items
# no longer returned. Keep human annotations in separate exemplar files.
python collect_youtube.py refresh --input candidates.jsonl \
  --out candidates.jsonl --overwrite

# Offline unit tests: no network or API key required.
python -m unittest -v test_collector
```

The collector deduplicates by video ID within a run and preserves the video API
resource separately from its own discovery bookkeeping. It does not inspect
frames, rank physical correctness, download audiovisual media, buy files, or
certify licenses. Cross-run and cross-URL visual deduplication still needs your
review: a Short and a full video can contain the same simulation.

Search results and counts change over time; log your query, execution date, and
curation decisions. Check your project's current quota before a large batch.
Google's quota documentation checked on 13 September 2026 lists a separate default
100-search-call daily bucket, and 10,000 daily units for other endpoints combined.
Additional search pages use additional calls. The command above requests eight
search pages, plus batched metadata reads. Network retries can consume more calls.
Do not rotate projects or credentials to evade quota limits.

API data is not a permanent archive. The tool adds `api_refresh_or_delete_by`, but
it does NOT run a scheduler or enforce deletion on your computer. Set your own
refresh/deletion process within the applicable retention period (generally 30
days for this public metadata use). Review the full API policies before deploying
this as a service, particularly privacy, storage, display, and derived-data rules.
Do not compute popularity-derived quality scores from API metrics; this collector
does not request view/like statistics. Your visual curation is independently
performed on authorized media, not claimed to be a YouTube metric.

## What qualifies

Use at least two distinct physical beats in a causally readable continuous shot,
including an interaction between an object and another object or environment.
For example, sustained acceleration down a ramp followed by a ricochet qualifies;
a single impact tagged both `collision` and `bounce` should not be counted twice.
This is a deliberately stricter curation rule than merely having two labels.

Record objects, event times, evidence frames, event order, physical material,
control mode, geometry evidence, and uncertainty. Near misses and grazes need
special review because projection, blur, and missed frames can hide contact.
Measure actual 3D surface distances only when geometry is available. An apparent
2D gap is not proof of a small 3D clearance.

Proposed score: 0-2 each for physical plausibility, event legibility, spatial
composition, transferability, and reconstructability. Start at >=8/10, with 2 in
plausibility and legibility. This is an initial heuristic, not a validated metric.
Review uncertain cases rather than making up physical parameters or rejecting
plausible hidden actuation without evidence. Human review is required before
promotion to accepted status.

Keep rigid, deformable, fluid, adhesive, and stylized merging examples in separate
lanes. Metaball surface blending alone is not a fluid simulation. A source file
with physics enabled is useful evidence but not a guarantee of stable contacts
or realistic parameters.

## Acquisition and rights

Use a creator-provided downloadable master, an expressly permitted download, or
your own render from an appropriately licensed .blend. Record the license and
permission evidence separately for the video, scene file, and embedded assets.
Ask specifically about using excerpts/project details in AI few-shot prompts and
about any intended distribution of the resulting reference package. Purchasing
an asset is not itself evidence that every downstream use is licensed.

YouTube discovery and media acquisition are separate. The Data API is not a video
download API. Its policies restrict downloading/caching YouTube audiovisual
content without YouTube's prior written approval. A Creative Commons search
filter is a useful lead, not permission to ignore platform rules or third-party
rights. The FFmpeg recipes operate only on already-authorized local files.

The Sisyphus listing is marked CC-BY-NC and contains old download-problem reports;
file retrieval and modern Blender compatibility were not verified here. The Alan
Luk listing explicitly pairs the third user video with a .blend, textures, and
render deliverables. Its intended prompting/redistribution rights remain to be
confirmed; the package was not bought or downloaded.

## Building a small useful corpus

Suggested initial goal, not a performance guarantee: 40-60 accepted clips covering
all eight families, with at least 12 reconstruction-tested examples. Favor event
pair and geometric diversity rather than many copies of one marble machine.
Keep perhaps 20% as held-out evaluation material, split by creator/scene family
before generating variants. Every crop, camera variant, and parameter variation
from one base scene belongs to the same split.

Track acceptance rate per query family, novel event pairs added, source-project
availability, unresolved rights, and reconstruction pass rate. These are metrics
of your own curation workflow, not derived YouTube popularity metrics. When a
family yields few suitable clips, change the mechanism vocabulary or construct a
controlled example instead of weakening the physics gate.

Kubric/MOVi is an optional supplemental source: it uses PyBullet for simulation
and Blender for rendering and includes trajectory/collision annotations. Label
that distinction; it is not evidence of native Blender solver configuration.
Use it for simple physical anchors and tests, not as a substitute for curated
creative staging. Verify the chosen dataset and asset licenses separately.

## Verification performed on this kit

The collector was syntax-checked and exercised with mocked API responses for
query pagination/deduplication, batched video retrieval, missing videos, channel
pagination, and file I/O. A synthetic local video was used to test clip/frame
extraction commands. Live YouTube API execution requires your key and was not
performed. No reference videos were downloaded or annotated at frame level.
