"""Small persisted-byte and evaluated-state helpers; no Blender import."""
import hashlib
import json
from pathlib import Path

VERSION = 'blender-production-1'
ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def data_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def read(path):
    return json.loads(Path(path).read_text())


def source_hashes():
    # Freeze the production inputs independently of downstream reviews/exports.
    paths=['modules/blender/production/'+name for name in
           ('__init__.py','__main__.py','common.py','driver.py','scenes.py','analytic.py')]
    paths += ['modules/blender/batch.py','modules/blender/recipes.py','modules/blender/geometry.py',
              'modules/blender/executables.py']
    return {name:digest(ROOT/name) for name in sorted(paths)}


def rows(path):
    with Path(path).open() as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
