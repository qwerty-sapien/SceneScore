"""Build the existing verified local bundle and serve it on one loopback origin."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import uvicorn


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024..65535')
    subprocess.run([sys.executable, 'apps/web/tools/prepare.py', '--assets-root', 'artifacts',
                    '--out', 'apps/web/public/studio'], cwd=root, check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
    print(f'SceneScore PID={os.getpid()} http://127.0.0.1:{args.port} — keyboard / labelled synthetic replay; Ctrl-C stops.', flush=True)
    uvicorn.run('scenescore.service:app', host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
