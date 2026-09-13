"""Explicit Phase3A data audit; no training without eligible real sessions."""

import argparse
import json
from pathlib import Path
from .pipeline import encoded
from .readiness import freeze_index, readiness_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("private_data/02A"))
    parser.add_argument("--index", type=Path)
    parser.add_argument("--freeze-assignments", type=Path, help="Freeze preassigned whole sessions/refits; output is exclusive")
    parser.add_argument("--output", type=Path, default=Path("reports/03A/data-audit.json"))
    parser.add_argument("--quality-profile-out", type=Path, help="Calibrate numeric signal gates from audited train sessions")
    args = parser.parse_args(argv)
    if args.quality_profile_out and (not args.index or args.freeze_assignments):
        parser.error('--quality-profile-out requires an existing frozen --index, separate from index creation')
    if args.freeze_assignments:
        result = freeze_index(args.data_root, json.loads(args.freeze_assignments.read_text())["sessions"], args.output)
        print(json.dumps(result, indent=2))
        return 0
    if args.index and not args.index.is_file():
        raise ValueError("requested_index_does_not_exist")
    index = json.loads(args.index.read_text()) if args.index else None
    result = readiness_report(args.data_root, index=index)
    if args.quality_profile_out:
        from modules.muse.acquisition.store import manifest, replay
        from modules.muse.runtime.quality import calibrate_profile
        sessions = []
        # readiness_report has audited every role and content hash before this fit.
        for entry in index['sessions']:
            if entry['role'] != 'train':
                continue
            session = args.data_root / entry['path']
            sessions.append({**entry, 'metadata': manifest(session)['metadata'],
                             'chunks': list(replay(session)),
                             'labels': [json.loads(line) for line in (session / 'labels.jsonl').read_text().splitlines()]})
        if not sessions:
            raise ValueError('audited_training_sessions_required')
        profile = calibrate_profile(sessions[0]['metadata'], sessions)
        args.quality_profile_out.parent.mkdir(parents=True, exist_ok=True)
        with args.quality_profile_out.open('xb') as stream:
            stream.write(encoded(profile))
        result['signal_quality_profile'] = {'path': str(args.quality_profile_out), 'sha256': profile['sha256'],
                                            'scope': 'numeric_signal_only_contact_and_accuracy_unmeasured'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(result))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    main()
