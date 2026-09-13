"""Freeze the existing public site and stage only the requested gallery additions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/vercel-animations-06-08-18'
BASE = ROOT / 'artifacts/vercel-video-publication-base-v2'
STAGE = ROOT / 'artifacts/vercel-video-publication'
BUILD = ROOT / 'artifacts/vercel-video-build'
LIVE = 'https://scenescore-muse-vertical.vercel.app'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def files(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*')) if p.is_file() and '.vercel' not in p.parts}


def fetch():
    if BASE.exists():
        raise ValueError('Preserve the existing publication snapshot')
    BASE.mkdir()
    paths = json.loads((REPORT / 'live-file-paths.json').read_text())
    def get(source):
        assert source.startswith('src/')
        relative = source.removeprefix('src/')
        assert '..' not in PurePosixPath(relative).parts
        target = BASE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--max-time', '30',
                        '--max-filesize', str(128*1024**2), LIVE+'/'+quote(relative), '-o', str(target)],
                       check=True, timeout=35)
        return relative
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert len(list(pool.map(get, paths))) == len(paths)
    dump(REPORT / 'base-manifest.json', dict(deployment_id='dpl_epKeMBmK5hCzdaaSFdkvEnTZMYkp', files=files(BASE)))
    print(json.dumps(dict(snapshot_files=len(paths))))


def assemble():
    if STAGE.exists():
        raise ValueError('Preserve staged publication')
    assert files(BASE) == json.loads((REPORT / 'base-manifest.json').read_text())['files']
    shutil.copytree(BASE, STAGE)
    shutil.copy2(BUILD / 'index.html', STAGE / 'index.html')
    shutil.copytree(BUILD / 'assets', STAGE / 'assets', dirs_exist_ok=True)
    public = ROOT / 'apps/web/public/requested-animations'
    entries = json.loads((public / 'catalog.json').read_text())['entries']
    additions = {}
    target = STAGE / 'requested-animations'
    target.mkdir()
    for entry in entries:
        bundle_path = public / entry['url']
        assert digest(bundle_path) == entry['sha256']
        b = json.loads(bundle_path.read_text())
        assert digest(public / b['video']) == b['video_sha256']
        shutil.copy2(bundle_path, target / entry['url'])
        shutil.copy2(public / b['video'], target / b['video'])
        key = b['video_sha256']
        if key not in additions:
            additions[key] = dict(id=key, title=b['title'], duration=b['scene']['duration_s'],
                video='/requested-animations/'+b['video'], video_sha256=key,
                label=b['animation_label'], source='prepared', audio='live', entries=[])
        additions[key]['entries'].append({**entry, 'url':'/requested-animations/'+entry['url']})
    additions = list(additions.values())
    assert len(additions) == 3 and all(len(v['entries']) == 3 for v in additions)
    shutil.copy2(public / 'catalog.json', target / 'catalog.json')
    catalog = json.loads((BASE / 'library/catalog.json').read_text())
    previous_ids = {v['id'] for v in catalog['videos']}
    catalog['videos'] = [v for v in additions if v['id'] not in previous_ids] + catalog['videos']
    dump(STAGE / 'library/catalog.json', catalog)
    dump(STAGE / 'vercel.json', dict(version=2, framework=None, buildCommand=None))
    (STAGE / '.vercel').mkdir()
    shutil.copy2('/private/tmp/scenescore-minimal-trainer-publication/.vercel/project.json', STAGE / '.vercel/project.json')
    source_paths = [ROOT / p for p in ['packages/audio/engine.ts', 'packages/audio/piano-voices.ts',
                    'packages/audio/model.ts', 'apps/web/src/main.tsx', 'apps/web/tools/prepare_requested_videos.py']]
    dump(REPORT / 'publication-manifest.json', dict(stage=str(STAGE), base_deployment_id='dpl_epKeMBmK5hCzdaaSFdkvEnTZMYkp',
        files=files(STAGE), source_hashes={str(p.relative_to(ROOT)): digest(p) for p in source_paths},
        videos=[dict(title=v['title'], video=v['video'], sha256=v['video_sha256']) for v in additions],
        authority='User requested Blender animations 6, 8 and 18 with backing music and sound effects on Vercel; explicitly excluded C.'))
    verify()


def verify():
    expected = json.loads((REPORT / 'publication-manifest.json').read_text())
    assert files(STAGE) == expected['files']
    old = json.loads((REPORT / 'base-manifest.json').read_text())['files']
    preserved = [p for p in old if p not in ['index.html', 'library/catalog.json']]
    assert all(digest(STAGE / p) == old[p] for p in preserved)
    catalog = json.loads((STAGE / 'library/catalog.json').read_text())
    assert not any(p.name.lower() == 'c.mp4' for p in STAGE.rglob('*'))
    for item in catalog['videos']:
        media = STAGE / item['video'].lstrip('/')
        expected_video = item.get('video_sha256', item['id'])
        assert digest(media) == expected_video
        for entry in item['entries']:
            path = STAGE / entry['url'].lstrip('/')
            assert digest(path) == entry['sha256']
            bundle = json.loads(path.read_text())
            assert digest(path.parent / bundle['video']) == bundle['video_sha256']
    result = dict(status='PASSED', videos=len(catalog['videos']), additions=len(expected['videos']),
                  existing_files_preserved=len(preserved), bytes=sum((STAGE / p).stat().st_size for p in expected['files']),
                  files=len(expected['files']))
    dump(REPORT / 'staging-validation.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['fetch', 'assemble', 'verify'])
    globals()[parser.parse_args().stage]()
