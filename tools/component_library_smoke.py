"""Bounded host entry point for the fixed-component Blender construction smoke."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    from modules.blender.batch import bounded
    from modules.blender.executables import blender_executable
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new artifact directory')
    parser.add_argument('--receipt', type=Path, required=True, help='new execution receipt JSON')
    parser.add_argument('--blender')
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 300:
        parser.error('timeout must be 1..300 seconds')
    out, receipt = args.out.resolve(), args.receipt.resolve()
    log = receipt.with_suffix('.log')
    if out.exists() or receipt.exists() or log.exists():
        parser.error('output, receipt and log must be new paths')
    command = [blender_executable(args.blender), '--background', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1', '--threads', '2', '--python',
               str(ROOT/'modules/blender/tests/blender_components_smoke.py'), '--', str(out)]
    result = bounded(command, log, args.timeout)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    smoke = out/'smoke.json'
    if result['status'] == 'passed' and (not smoke.exists() or json.loads(smoke.read_text()).get('status') != 'PASSED'):
        result.update(status='failed', error='Blender exited without a passing smoke artifact')
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, sort_keys=True))
    return int(result['status'] != 'passed' or not result['process_group_absent'])


if __name__ == '__main__':
    raise SystemExit(main())
