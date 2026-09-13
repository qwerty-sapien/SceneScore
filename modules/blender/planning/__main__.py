"""Validate scene_intent.json/yaml into two explicit planning artifacts."""
import argparse
import json
from pathlib import Path
from .io import load_plan, write_outputs
from .validator import validate_plan
from .contracts import RESOLVED_VERSION


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', required=True, type=Path, help='new output directory; never overwrites earlier constraints')
    args = parser.parse_args(argv)
    try:
        report, resolved = validate_plan(load_plan(args.input))
    except (ValueError, TypeError, OSError, ImportError) as error:
        report = {'status': 'FAILED', 'errors': [{'code': 'INVALID_INPUT', 'message': str(error)}], 'physics_validated': False}
        resolved = {'schema_version': RESOLVED_VERSION, 'status': 'BLOCKED', 'constraints': None}
    try:
        write_outputs(args.out, report, resolved)
    except OSError as error:
        parser.error(str(error))
    print(json.dumps({'status': report['status'], 'errors': len(report.get('errors', [])), 'warnings': len(report.get('warnings', [])), 'out': str(args.out)}))
    return int(report['status'] != 'PASSED')


if __name__ == '__main__':
    raise SystemExit(main())
