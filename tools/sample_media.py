"""One-shot stratified sample of current review deliverables, not historical intermediates."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import secrets

from modules.blender.selection import selected_bundle, staged_bundle


def main():
    root = Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    selections=parser.add_mutually_exclusive_group()
    selections.add_argument('--selection',type=Path)
    selections.add_argument('--review-selection',type=Path)
    parser.add_argument('--deliverables',type=Path,help='new exact selection-bound music and preview paths')
    parser.add_argument('--out',type=Path,default=root/'reports/media-evaluation/sample.json')
    parser.add_argument('--protocol',type=Path,default=root/'reports/media-evaluation/PROTOCOL.md')
    args=parser.parse_args()
    out=args.out
    selected_scenes=([staged_bundle(args.review_selection)] if args.review_selection else
                     [selected_bundle(v,args.selection) for v in ('hero','near_miss')])
    if out.exists():
        raise SystemExit('Sample already frozen; no redraw permitted')
    groups = {
        'music': sorted((root / 'artifacts/music/review-v2').glob('*/*/mix.wav')),
        'scene': [p/'preview.mp4' for p,_ in selected_scenes],
        'preview': [root / 'artifacts/arranger/evaluated-hero-audition/baseline.wav',
                    root / 'artifacts/arranger/evaluated-hero-audition/transition.wav',
                    root / 'artifacts/phase3/performance/scenescore-DRAFT.mp4'],
    }
    if args.deliverables:
        inputs=json.loads(args.deliverables.read_text())
        if inputs.get('version')!='media-review-deliverables-1' or inputs.get('scene_selection_sha256')!=selected_scenes[0][1]['selection_sha256']:
            raise ValueError('review_deliverables_not_bound_to_selection')
        for group in ('music','preview'):
            groups[group]=[(root/p).resolve() for p in inputs[group]]
            if any(not p.is_relative_to(root) for p in groups[group]):
                raise ValueError('review_deliverable_outside_repository')
    elif any(not s['legacy_choreography'] for _,s in selected_scenes):
        raise ValueError('new_selection_requires_matching_review_deliverables')
    if len(groups['music'])<2 or not groups['scene'] or not groups['preview']:
        raise ValueError('incomplete_review_strata')
    seed = secrets.randbits(64)
    rng = random.Random(seed)
    universe = []
    selected = []
    for group, paths in groups.items():
        entries = [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'stratum': group} for p in sorted(paths)]
        universe += entries
        selected += rng.sample(entries, 2 if group == 'music' else 1)
    record = {'version': 'media-review-sample-1', 'seed': seed, 'algorithm': 'Python random.Random.sample, sorted paths per stratum',
              'universe_count': len(universe), 'sample_count': len(selected), 'fraction': len(selected) / len(universe),
              'universe': universe, 'selected': selected, 'scene_selections':[s for _,s in selected_scenes],
              'protocol_sha256': hashlib.sha256(args.protocol.read_bytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'seed': seed, 'sample_count': len(selected), 'universe_count': len(universe), 'selected': selected}, indent=2))


if __name__ == '__main__':
    main()
