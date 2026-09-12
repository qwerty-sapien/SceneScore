"""Explicit Phase3A data audit; no training without eligible real sessions."""

import argparse
import json
from pathlib import Path
from .pipeline import audit_real, encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("private_data/02A"))
    parser.add_argument("--index", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/03A/data-audit.json"))
    args = parser.parse_args()
    if not args.data_root.is_dir() or not args.index or not args.index.is_file():
        result = {
            "status": "INSUFFICIENT_REAL_DATA",
            "release_status": "PIPELINE_TESTED_ONLY",
            "trained_models": 0,
            "real_evaluation": "NOT_RUN",
            "data_root_exists": args.data_root.is_dir(),
            "reason": "No frozen index of consented verified real sessions and independent labels",
        }
    else:
        result = {
            "status": "REAL_DATA_AUDITED_NOT_TRAINED",
            "sessions": audit_real(args.data_root, json.loads(args.index.read_text())),
            "trained_models": 0,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
