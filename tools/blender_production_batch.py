"""Serial trusted production jobs; each Blender child has its own bounded ledger."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('jobs',type=Path,help='JSON list: out, recipe, variant, seconds, stages, optional solver values')
    args=parser.parse_args()
    for job in json.loads(args.jobs.read_text()):
        for stage in job.get('stages',['build','bake','replay','verify-replay']):
            cmd=[sys.executable,'-m','modules.blender.production',stage,'--out',job['out']]
            for key in ('recipe','variant','seconds','physics_hz','solver_substeps','solver_iterations','profile','camera','first','last','parameters'):
                if key in job:
                    cmd+=['--'+key.replace('_','-'),str(job[key])]
            result=subprocess.run(cmd,timeout=1850)
            if result.returncode:
                return result.returncode
    return 0


if __name__=='__main__':
    raise SystemExit(main())
