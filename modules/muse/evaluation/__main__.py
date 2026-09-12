import argparse
import json
from pathlib import Path
from .events import Matcher, match


def main():
    parser = argparse.ArgumentParser(description="Evaluate a complete, frozen labelled session stream.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=0.75)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    report = match(**data, config=Matcher(args.tolerance))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
