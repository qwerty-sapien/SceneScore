"""Build the existing verified local bundle and serve it on one loopback origin."""
import argparse
import os
import json
from pathlib import Path
import subprocess
import sys

import uvicorn


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    selections=parser.add_mutually_exclusive_group()
    selections.add_argument('--selection',type=Path,help='exact verified candidate selection; default active or frozen legacy')
    selections.add_argument('--review-selection',type=Path,help='explicit staged review; served at /?review=1')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024..65535')
    command=[sys.executable,'apps/web/tools/prepare.py','--assets-root','artifacts','--out',
             'apps/web/public/blender-review' if args.review_selection else 'apps/web/public/studio']
    if args.selection:
        command+=['--selection',str(args.selection.resolve())]
    if args.review_selection:
        command+=['--review-selection',str(args.review_selection.resolve())]
    subprocess.run(command,cwd=root,check=True)
    if not args.review_selection:
        catalog=json.loads((root/'apps/web/public/studio/catalog.json').read_text())
        first=json.loads((root/'apps/web/public/studio'/catalog['entries'][0]['url']).read_text())
    if not args.review_selection and first['scene']['duration_s']==30 and first['selection']['legacy_choreography']:
        subprocess.run([sys.executable,'tools/prepare_collision_riffs.py'],cwd=root,check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
    print(f'SceneScore PID={os.getpid()} http://127.0.0.1:{args.port} — keyboard / labelled synthetic replay; Ctrl-C stops.', flush=True)
    uvicorn.run('scenescore.service:app', host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
