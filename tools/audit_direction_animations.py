"""Read-only, persisted-byte/clock/replay/cleanup audit of chosen animation outputs."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.blender.production.common import digest, read  # noqa: E402


def audit(candidate):
    provenance = read(candidate / 'provenance.json')
    for name, expected in provenance['input_hashes'].items():
        assert digest(candidate / name) == expected, name
    for name, expected in provenance['source_hashes'].items():
        assert digest(candidate / 'generation_source' / name) == expected, name
    build, replay, media = (read(candidate / name) for name in ('build.json', 'replay.json', 'media_validation.json'))
    for report in (build, replay, media, read(candidate / 'packet_validation.json'),
                   read(candidate / 'simulation_reopen_validation.json'), read(candidate / 'replay_validation.json')):
        assert report['status'] == 'PASSED'
    assert build['simulation_sha256'] == digest(candidate / 'simulation.blend') == replay['simulation_sha256']
    assert build['geometry_sha256'] == digest(candidate / 'evaluated_geometry.json')
    assert replay['scene_sha256'] == digest(candidate / 'scene.blend') == media['scene_sha256']
    assert replay['mechanics_states_sha256'] == digest(candidate / 'mechanics_states.jsonl')
    assert media['video_sha256'] == digest(candidate / 'renders/video.mp4')
    assert media['duration_s'] == 30 and media['frames'] == 900 and media['fps'] == 30
    assert media['full_decode'] is True and media['approval'] is None
    jobs = [read(p) for p in sorted((candidate / 'jobs').glob('*.job.json'))]
    assert jobs and all(j['status'] == 'passed' and j['process_group_absent'] for j in jobs)
    return dict(candidate=str(candidate), status='PASSED', video=media,
                computed_states_sha256=provenance['input_hashes']['mechanics_states.jsonl'],
                source_files=len(provenance['source_hashes']), jobs=len(jobs),
                job_seconds=sum(j['duration_s'] for j in jobs),
                mechanics_scope=read(candidate / 'packet.json')['backend'],
                scope='byte lineage, computed clock, fresh replay, complete movie cadence/decode and job receipts; not human acceptance')


def teardown(artifact_root):
    jobs = []
    live = []
    for path in sorted(artifact_root.rglob('*.job.json')):
        job = read(path)
        pid = job.get('pgid')
        if pid is None:
            continue
        try:
            os.killpg(pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        except PermissionError:
            absent = False
        jobs.append(dict(receipt=str(path), pgid=pid, recorded_absent=job.get('process_group_absent'),
                         currently_absent=absent, status=job['status']))
        if not absent:
            live.append(pid)
    assert not live, 'Unresolved recorded process groups: ' + str(live)
    return dict(status='PASSED', jobs=jobs, live_groups=live, method='read-only killpg(pgid,0); no signal sent')


def geometry_evidence(candidates):
    directory = ROOT / 'reports/animation-directions-06-08-18/gate-evaluated'
    path = directory / 'FINAL-SCOPED-GATE.json'
    gate = read(path)
    assert gate['status'] == 'PASSED_SCOPED_EVALUATED_STATIC_GEOMETRY'
    selected = {p.name for p in candidates}
    assert set(gate['candidates']).issubset(selected)
    for name, expected in gate['evidence_sha256'].items():
        assert digest(directory / name) == expected, name
    for name in ('RESULTS-06-v4.json', 'RESULTS-08-final-evaluated-v3.json'):
        for input_name, expected in read(directory / name)['input_sha256'].items():
            assert digest(ROOT / input_name) == expected, input_name
    return dict(report=str(path), report_sha256=digest(path),
                status=gate['status'], candidates=gate['candidates'],
                scope_limits=gate['scope_limits'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidates', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    baseline = read(ROOT / 'reports/animation-directions-06-08-18/reference-baseline.json')
    for name, expected in baseline['hashes'].items():
        assert digest(Path(baseline['reference']) / name) == expected, 'Reference changed: ' + name
    report = dict(status='PASSED', reference_preserved=True,
        candidates=[audit(p.resolve()) for p in args.candidates],
        independent_geometry_evidence=geometry_evidence(args.candidates),
        teardown=teardown(ROOT / 'artifacts/blender/revamp/directions'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], candidates=len(report['candidates']),
                         reference_preserved=True, job_groups_absent=len(report['teardown']['jobs']))))


if __name__ == '__main__':
    main()
