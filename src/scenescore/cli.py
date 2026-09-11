"""Root commands for the bounded Phase 1 harness."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
from .contracts import ROOT, SCHEMA, VALIDATOR, load_json, validate, content_hash


def fixtures():
    VALIDATOR.check_schema(SCHEMA)
    results = []
    for case in load_json(ROOT / "fixtures/manifest.json"):
        try:
            validate(load_json(ROOT / case["path"]))
            actual = True
        except ValueError:
            actual = False
        results.append({"path": case["path"], "expected_valid": case["valid"], "actual_valid": actual})
    ok = all(r["expected_valid"] == r["actual_valid"] for r in results)
    return {"status": "passed" if ok else "failed", "checks": results, "evidence_mode": "synthetic"}


def doctor():
    import importlib.metadata as metadata
    checks = []
    def add(name, status, evidence):
        checks.append({"name": name, "status": status, "evidence": evidence})
    add("python", "available" if sys.version_info[:2] == (3,13) else "conflict", sys.version.split()[0])
    add("python_build_platform", "observed_runtime_metadata", sysconfig.get_platform())
    for package in ["jsonschema", "fastapi", "uvicorn", "pydantic"]:
        try:
            add(package, "available", metadata.version(package))
        except metadata.PackageNotFoundError:
            add(package, "unavailable", "run make install")
    for tool in ["node", "npm", "uv"]:
        path = shutil.which(tool)
        if path:
            result = subprocess.run([path, "--version"], text=True, capture_output=True, timeout=10)
            add(tool, "available" if result.returncode == 0 else "unavailable", result.stdout.strip())
        else:
            add(tool, "unavailable", "required harness tool missing")
    profile = Path.home() / ".config/agent-context/host-capabilities.json"
    if profile.exists():
        p = load_json(profile)
        add("host_identity", "captured_input", {"profile_id": p["profile_id"], "architecture": p["host"]["architecture"]})
    else:
        add("host_identity", "unverified", "CI or host profile unavailable; no host facts inferred")
    ragtm = Path(os.environ.get("RAGTM_PATH") or ROOT / "RageAgainstTheMachine-main")
    add("ragtm_source", "available" if (ragtm/"AGENTS.md").is_file() else "unverified", "source presence only; never executed")
    configured = os.environ.get("BLENDER_BIN")
    candidates = [Path(configured)] if configured else [Path('/Applications/Blender.app/Contents/MacOS/Blender')]
    found = next((p for p in candidates if p.is_file()), None)
    if found:
        result = subprocess.run([str(found), "--version"], text=True, capture_output=True, timeout=10)
        add("blender", "available" if result.returncode == 0 else "unverified", result.stdout.splitlines()[:1])
    else:
        add("blender", "unverified", "BLENDER_BIN and standard app path unavailable; rendering not required for Phase 1")
    add("blender_python", "unverified", "No Blender Python was launched")
    add("muse", "unverified", "Generation, channels, units, rate and transport require an actual session")
    add("bluetooth_permission", "unverified", "No permission prompt or capture performed")
    add("browser_audio", "unverified", "Browser must unlock AudioContext by user gesture; output has not been tested")
    configured_api = bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL"))
    add("model_api", "unverified", "configuration present; explicit preflight required" if configured_api else "key/model pair not configured; no model ID invented")
    required = [c for c in checks if c["name"] in ('python','jsonschema','fastapi','uvicorn','pydantic','node','npm','uv')]
    return {"status": "passed" if all(c["status"] == "available" for c in required) else "failed", "scope": "Phase 1 software prerequisites only", "checks": checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["doctor", "test-contracts", "dev-replay", "assets", "demo", "run-task"])
    parser.add_argument("--task", default="01")
    parser.add_argument("--check", choices=["doctor", "test-contracts"], default="test-contracts")
    args = parser.parse_args()
    if args.command in ("dev-replay", "assets", "demo"):
        print(json.dumps({"status": "NOT_IMPLEMENTED", "command": args.command, "next": "requires Phase 2 modules / Phase 3B integration; use make test-contracts for synthetic checks"}))
        return 2
    if args.command == "run-task":
        if args.task != "01":
            print(json.dumps({"status": "PHASE_NOT_AUTHORIZED", "task": args.task}))
            return 2
        result = doctor() if args.check == "doctor" else fixtures()
        task = load_json(ROOT / "tools/tasks.json")["01"]
        result = {**result, "task": "01", "owner": task["owner"], "dependencies": task["dependencies"], "command": args.check,
                  "schema_hash": content_hash((ROOT/"contracts/0.1/schema.json").read_bytes())}
        destination = ROOT / "artifacts/harness/task-01.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2)+"\n")
    else:
        result = doctor() if args.command == "doctor" else fixtures()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
