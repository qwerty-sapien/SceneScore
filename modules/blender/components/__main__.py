"""Assemble serialized component geometry without starting Blender."""
import argparse
import json
from pathlib import Path
from modules.blender.planning.io import load_plan
from .connections import assemble_route, assemble_resolved, RouteValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout', type=Path)
    parser.add_argument('--resolved', type=Path, help='A4 constraints to bind and revalidate')
    parser.add_argument('--out', type=Path, required=True, help='new JSON artifact')
    args = parser.parse_args(argv)
    try:
        layout = load_plan(args.layout)
        result = assemble_resolved(load_plan(args.resolved), layout) if args.resolved else assemble_route(layout).to_dict()
    except (ValueError, TypeError, OSError, RecursionError) as error:
        result = {'status': 'FAILED', 'error': str(error), 'physics_validated': False}
        if isinstance(error, RouteValidationError):
            result['connection_reports'] = error.reports
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x') as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
    except OSError as error:
        parser.error(str(error))
    print(json.dumps({'status': result['status'], 'out': str(args.out)}))
    return int(result['status'] == 'FAILED')


if __name__ == '__main__':
    raise SystemExit(main())
