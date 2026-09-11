"""Exact capability dispatch; only local contract validation is implemented."""
import json
import threading
import time
from pathlib import Path
from .contracts import ROOT, validate, content_hash


class CapabilityError(ValueError):
    pass


class Registry:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.entries = {e["id"]: e for e in json.loads((ROOT / "tools/capabilities.yaml").read_text())["capabilities"]}
        self.lock = threading.Lock()

    def run(self, request):
        validate(request)
        name = request["capability_id"]
        if name not in self.entries:
            raise CapabilityError("UNKNOWN_CAPABILITY")
        entry = self.entries[name]
        if request["timeout_s"] > entry["timeout_seconds"] or request["max_concurrency"] > entry["concurrency_limit"]:
            raise CapabilityError("BUDGET_EXCEEDED")
        output = Path(request["output_path"])
        if output.is_absolute() or ".." in output.parts:
            raise CapabilityError("OUTPUT_PATH_DENIED")
        output = (self.root / output).resolve()
        allowed = [(self.root / p).resolve() for p in entry["allowed_output_paths"]]
        if not any(output.is_relative_to(p) and p.is_relative_to(self.root) for p in allowed):
            raise CapabilityError("OUTPUT_PATH_DENIED")
        artifact = validate(request["input"])
        if entry["input_schema"] != "SceneScoreRecord" and artifact["kind"] != entry["input_schema"]:
            raise CapabilityError("INPUT_KIND_MISMATCH")
        if entry["implementation_status"] != "IMPLEMENTED":
            raise CapabilityError("NOT_IMPLEMENTED: " + name + "; see phase ownership")
        if not self.lock.acquire(blocking=False):
            raise CapabilityError("CONCURRENCY_EXCEEDED")
        try:
            start = time.monotonic()
            if name != "contracts.validate":
                raise CapabilityError("ADAPTER_NOT_REGISTERED")
            # No arbitrary process/plugin entrypoint. New adapters need lifecycle tests before registration.
            payload = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            schema_hash = content_hash((ROOT / "contracts/0.1/schema.json").read_bytes())
            key = content_hash(payload + schema_hash.encode() + entry["adapter_version"].encode())
            cache = self.root / "artifacts/harness/cache" / (key + ".json")
            if not cache.resolve().is_relative_to(self.root):
                raise CapabilityError("CACHE_PATH_DENIED")
            cached = cache.exists()
            if cached and cache.read_bytes() != payload:
                raise CapabilityError("CACHE_INTEGRITY_FAILED")
            validate(json.loads(payload))
            if time.monotonic() - start > request["timeout_s"]:
                raise CapabilityError("TIMEOUT")
            output.parent.mkdir(parents=True, exist_ok=True)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(payload)
            output.write_bytes(payload)
            return {"status": "passed", "capability": name, "cached": cached, "cache_key": key,
                    "output_hash": content_hash(payload), "schema_hash": schema_hash,
                    "source_mode": artifact["provenance"]["source_mode"], "output_path": str(output)}
        finally:
            self.lock.release()
