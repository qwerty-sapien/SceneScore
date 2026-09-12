"""One-shot stratified sample of current review deliverables, not historical intermediates."""
import hashlib
import json
from pathlib import Path
import random
import secrets


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / 'reports/media-evaluation/sample.json'
    if out.exists():
        raise SystemExit('Sample already frozen; no redraw permitted')
    groups = {
        'music': sorted((root / 'artifacts/music/review-v2').glob('*/*/mix.wav')),
        'scene': [root / 'artifacts/blender/validated-hero/10_projectile_tower-default/preview.mp4',
                  root / 'artifacts/blender/final-near-miss/10_projectile_tower-near_miss/preview.mp4'],
        'preview': [root / 'artifacts/arranger/evaluated-hero-audition/baseline.wav',
                    root / 'artifacts/arranger/evaluated-hero-audition/transition.wav',
                    root / 'artifacts/phase3/performance/scenescore-DRAFT.mp4'],
    }
    assert {key: len(value) for key, value in groups.items()} == {'music': 12, 'scene': 2, 'preview': 3}
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
              'universe': universe, 'selected': selected, 'protocol_sha256': hashlib.sha256((out.parent / 'PROTOCOL.md').read_bytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'seed': seed, 'sample_count': len(selected), 'universe_count': len(universe), 'selected': selected}, indent=2))


if __name__ == '__main__':
    main()
