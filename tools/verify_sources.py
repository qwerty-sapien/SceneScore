"""Check immutable planning inputs without inspecting or executing RAGTM code."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected = json.loads((root/'.brief/CHECKSUMS.json').read_text())
for name, digest in expected.items():
    data = (root/'.brief'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, name
    assert (root/'planning/scene_score_codex_pack'/name).read_bytes() == data, name
print(f"Immutable input checks passed: {len(expected)} supplied hashes and planning copies")
