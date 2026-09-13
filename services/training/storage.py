"""Bounded raw reader with exact-byte cache keys and kind-specific canonical validation."""

from collections import OrderedDict
import hashlib
import json
import math
import threading
from jsonschema import Draft202012Validator, ValidationError
from modules.muse.acquisition.store import check_pair
from scenescore.contracts import SCHEMA, semantic

LIMIT = 32 * 1024 * 1024
VALIDATORS = {
    kind: Draft202012Validator({"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/" + kind})
    for kind in ("EEGChunk", "AcquisitionMetadata")
}


def validate(value, kind):
    def finite(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non_finite_raw_value")
        if isinstance(item, dict):
            for nested in item.values():
                finite(nested)
        elif isinstance(item, list):
            for nested in item:
                finite(nested)

    finite(value)
    try:
        VALIDATORS[kind].validate(value)
    except ValidationError as exc:
        raise ValueError("canonical_raw_schema_invalid:" + exc.message[:120]) from exc
    semantic(value)
    return value


class RawCache:
    def __init__(self):
        self.cache, self.lock = OrderedDict(), threading.Lock()

    def read(self, path):
        with self.lock:
            files = [path / "manifest.json", path / "consent.json", *sorted((path / "chunks").glob("*.json"))]
            if len(files) > 20002 or (path / "chunks").is_symlink():
                raise ValueError("raw_file_capacity_or_symlink")
            size, digest, buffers = 0, hashlib.sha256(), []
            for file in files:
                if file.is_symlink():
                    raise ValueError("symlink_raw_file")
                size += file.stat().st_size
                if size > LIMIT:
                    raise ValueError("session_exceeds_32MiB_export_budget")
                raw = file.read_bytes()
                digest.update(str(file.relative_to(path)).encode())
                digest.update(raw)
                buffers.append(raw)
            key = (str(path), digest.hexdigest())
            if key in self.cache:
                result = self.cache.pop(key)
                self.cache[key] = result
                return result
            metadata = validate(json.loads(buffers[0])["metadata"], "AcquisitionMetadata")
            consent = json.loads(buffers[1])
            chunks, previous = [], None
            for file, raw in zip(files[2:], buffers[2:]):
                chunk = validate(json.loads(raw), "EEGChunk")
                if file.name != f"{chunk['sequence']:09d}.json" or not chunk["samples"]:
                    raise ValueError("chunk_name_or_samples_invalid")
                for field in ("session_id", "channels", "sample_rate_hz"):
                    if chunk[field] != metadata[field]:
                        raise ValueError("raw_metadata_mismatch")
                if chunk["provenance"]["source_mode"] != metadata["provenance"]["source_mode"]:
                    raise ValueError("source_mode_mismatch")
                check_pair(previous, chunk)
                previous = chunk
                chunks.append(chunk)
            result = {"metadata": metadata, "chunks": chunks, "consent": consent}
            self.cache[key] = result
            while len(self.cache) > 2:
                self.cache.popitem(last=False)
            return result

    def invalidate(self, path):
        with self.lock:
            for key in list(self.cache):
                if key[0] == str(path):
                    del self.cache[key]
