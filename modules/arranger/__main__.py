"""Explicit local-file interfaces. No service/API is started implicitly."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from .api import health
from .core import Context, Policy, baseline, compile_preview, encoded, exact_diff, import_plan
from .provider import Planner, public_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["health", "preview", "import", "summary", "propose", "diff"])
    parser.add_argument("--input", type=Path, help="JSON {context, policy?, brief?}")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--other", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/arranger/cache"))
    args = parser.parse_args()
    if args.command == "health":
        result = health()
    elif args.command == "diff":
        result = exact_diff(json.loads(args.plan.read_bytes()), json.loads(args.other.read_bytes()))
    else:
        data = json.loads(args.input.read_bytes())
        ctx, policy = Context(**data["context"]), Policy(**data.get("policy", {}))
        brief = data.get("brief", "Original blues/ragtime swing; restrained bossa accompaniment")
        if args.command == "summary":
            result = public_summary(ctx, brief)
        elif args.command == "propose":
            result = Planner(args.cache).propose(ctx, policy, brief)
        else:
            plan = import_plan(args.plan.read_bytes(), ctx, policy, brief) if args.command == "import" else baseline(ctx, policy, brief)
            result = {"plan": plan, "events": compile_preview(ctx, plan, policy, brief), "policy": asdict(policy),
                      "brief": brief, "audition_status": "AUDITION_PENDING", "approved": False}
    payload = encoded(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Manual import roundtrip retains exact approved-capable bytes as a separate file.
        if args.command == "import":
            args.output.with_suffix(".plan.json").write_bytes(args.plan.read_bytes())
        args.output.write_bytes(payload)
    else:
        print(payload.decode(), end="")


if __name__ == "__main__":
    main()
