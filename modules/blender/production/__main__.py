"""Explicit, serial production stages using the installed Blender executable."""
import argparse
from pathlib import Path
import shutil
import sys

from modules.blender.batch import bounded
from modules.blender.executables import blender_executable
from .common import ROOT, dump, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['build', 'bake', 'replay', 'verify-replay', 'export', 'render', 'validate'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--blender', help='executable; otherwise BLENDER_BIN, PATH, then platform default')
    parser.add_argument('--recipe', default='10_projectile_tower')
    parser.add_argument('--variant', choices=['contact', 'near_miss', 'no_launch', 'default'], default='contact')
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--physics-hz', type=int, default=240)
    parser.add_argument('--solver-substeps', type=int, default=10)
    parser.add_argument('--solver-iterations', type=int, default=60)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--profile', choices=['diagnostic', 'preview', 'final'], default='preview')
    parser.add_argument('--camera', choices=['beauty', 'side', 'top'], default='beauty')
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--parameters', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    artifact_root = (ROOT/'artifacts/blender/revamp').resolve()
    if not out.is_relative_to(artifact_root) or out == artifact_root:
        parser.error('output must be a candidate beneath artifacts/blender/revamp')
    if not 0 < args.seconds <= 30 or args.physics_hz not in (120, 240, 480, 960):
        parser.error('bounded seconds/physics rate required')
    if not 1 <= args.timeout <= 1800 or not 1 <= args.solver_substeps <= 100 or not 1 <= args.solver_iterations <= 1000:
        parser.error('invalid solver/job budget')
    if args.stage == 'build' and out.exists() and any(out.iterdir()):
        parser.error('build requires a new candidate directory')
    if shutil.disk_usage(ROOT).free < 3 * 1024**3:
        parser.error('less than 3 GiB free; stop before writing more artifacts')
    if args.stage == 'validate':
        from .validation import validate_candidate
        report = validate_candidate(out)
        dump(out/'physical-validation.json', report)
        print(report)
        return int(report.get('status') == 'FAILED')
    if args.stage == 'export':
        from .export import export_bundle
        export_bundle(out)
        return 0
    if args.stage == 'render' and args.profile != 'diagnostic':
        from .validation import validate_candidate
        proof=validate_candidate(out)
        if proof.get('status')!='PASSED':
            parser.error('production rendering requires current passed physical gates; use neutral diagnostics to inspect failures')
    try:
        args.blender = blender_executable(args.blender)
    except FileNotFoundError as error:
        parser.error(str(error))
    out.mkdir(parents=True, exist_ok=True)
    command = [args.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
               '--threads', '2', '--python', str(Path(__file__).with_name('driver.py')), '--', args.stage,
               '--out', str(out), '--recipe', args.recipe, '--variant', args.variant, '--seconds', str(args.seconds),
               '--physics-hz', str(args.physics_hz), '--solver-substeps', str(args.solver_substeps),
               '--solver-iterations', str(args.solver_iterations), '--seed', str(args.seed),
               '--profile', args.profile, '--camera', args.camera, '--first', str(args.first)]
    if args.last is not None:
        command += ['--last', str(args.last)]
    if args.parameters:
        command += ['--parameters', str(args.parameters.resolve())]
    name = f'{args.stage}-{args.profile}-{args.camera}-{args.first}'
    log = out/'jobs'/f'{name}.log'
    attempt = 1
    while log.exists():
        attempt += 1
        log = out/'jobs'/f'{name}-attempt{attempt}.log'
    cumulative = sum(read(p).get('duration_s', 0) for p in artifact_root.rglob('*.job.json'))
    if cumulative >= 14400:
        parser.error('four-hour cumulative Blender budget exhausted')
    size = sum(p.stat().st_size for p in artifact_root.rglob('*') if p.is_file())
    if size >= 20 * 1024**3:
        parser.error('20 GiB artifact budget exhausted')
    result = bounded(command, log, timeout=min(args.timeout, max(1, int(14400-cumulative))))
    print(result, flush=True)
    return 0 if result['status'] == 'passed' and result.get('process_group_absent') else 1


if __name__ == '__main__':
    sys.exit(main())
