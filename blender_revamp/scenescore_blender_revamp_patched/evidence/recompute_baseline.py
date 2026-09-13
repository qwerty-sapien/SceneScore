"""Read-only audit of supplied evaluated states, independent of repo geometry helpers.
Usage: python recompute_baseline.py /path/to/SceneScore /path/to/scenescore-DRAFT.mp4
This does not run Blender, certify the export, or evaluate animation aesthetics.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: recompute_baseline.py REPO_ROOT UPLOADED_MP4')
    root, video = map(Path, sys.argv[1:])
    bundle = root / 'artifacts/blender/validated-hero/10_projectile_tower-default'
    records = [json.loads(line) for line in (bundle / 'object_states.jsonl').read_text().splitlines() if line.strip()]
    grouped: dict[str, list[dict]] = {}
    for row in records:
        grouped.setdefault(row['object_id'], []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row['scene_time_s'])
    invariants = {}
    for oid, rows in grouped.items():
        dimensions = [[r['bounds_max_m'][i] - r['bounds_min_m'][i] for i in range(3)] for r in rows]
        invariants[oid] = {
            'samples': len(rows),
            'z_min_m': min(r['transform']['position_m'][2] for r in rows),
            'z_max_m': max(r['transform']['position_m'][2] for r in rows),
            'dimension_ranges_m': [[min(d[i] for d in dimensions), max(d[i] for d in dimensions)] for i in range(3)],
            'max_quaternion_component_deviation_from_initial': max(abs(r['transform']['quaternion_xyzw'][i] - rows[0]['transform']['quaternion_xyzw'][i]) for r in rows for i in range(4)),
            'initial_bounds_min_m': rows[0]['bounds_min_m'],
            'final_bounds_min_m': rows[-1]['bounds_min_m'],
        }
    overlaps = []
    for a, b in itertools.combinations(sorted(oid for oid in grouped if ':tower-' in oid), 2):
        aa, bb = grouped[a], grouped[b]
        if len(aa) != len(bb):
            raise ValueError('Mismatched sampling')
        best = None
        for ra, rb in zip(aa, bb):
            if ra['scene_time_s'] != rb['scene_time_s']:
                raise ValueError('Mismatched clocks')
            # Positive = axis separation; negative on all axes = overlap.
            q = [max(ra['bounds_min_m'][i] - rb['bounds_max_m'][i], rb['bounds_min_m'][i] - ra['bounds_max_m'][i]) for i in range(3)]
            signed = math.sqrt(sum(max(v, 0.0)**2 for v in q)) + min(max(q), 0.0)
            item = {'pair': [a,b], 't_s': ra['scene_time_s'], 'signed_gap_m': signed}
            if best is None or signed < best['signed_gap_m']:
                best = item
        overlaps.append(best)
    probe = subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)], check=True, capture_output=True, text=True)
    source_files = ['modules/blender/recipes.py','modules/blender/exporter.py','modules/blender/geometry.py','modules/blender/validate.py','modules/blender/batch.py','apps/web/tools/prepare.py','reports/media-evaluation/REVIEW.md']
    result = {
        'kind': 'read_only_baseline_analysis',
        'limitations': ['No Blender execution', 'Bounds and transforms come from supplied sidecars', 'Axis-aligned overlap is suitable here because recorded cube rotations are constant identity; it is insufficient for generally rotated meshes', 'No continuous-time collision guarantee from sampled states', 'No continuous playback or audio audition performed'],
        'uploaded_video_sha256': sha(video),
        'archive_video_sha256': sha(root/'artifacts/phase3/performance/scenescore-DRAFT.mp4'),
        'ffprobe': json.loads(probe.stdout),
        'source_sha256': {p: sha(root/p) for p in source_files},
        'bundle_sidecar_sha256': {p: sha(bundle/p) for p in ['object_states.jsonl','geometry.json','config.json','qa.json']},
        'object_invariants': invariants,
        'independently_recomputed_cube_minimum_gaps': overlaps,
    }
    print(json.dumps(result, indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
