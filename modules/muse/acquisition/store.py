"""Bounded local-only raw recorder. No filtering, device discovery, or upload."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile
from scenescore.contracts import validate

FORMAT = "scenescore.raw-session/1"
MAX_CHUNK_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 4096


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        os.chmod(temporary, 0o600)
        handle.write(encoded(value))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read_json(path):
    if path.stat().st_size > MAX_CHUNK_BYTES:
        raise ValueError("record_too_large")
    return json.loads(path.read_bytes())


def check_pair(previous, chunk):
    if previous is None:
        if chunk["sequence"] != 0 or chunk["sample_start_index"] != chunk["dropped_samples_before"]:
            raise ValueError("initial_indices")
        return
    if chunk["session_id"] != previous["session_id"]:
        raise ValueError("session_changed")
    if chunk["sequence"] != previous["sequence"] + 1:
        raise ValueError("sequence_discontinuity")
    if chunk["sample_start_index"] != (previous["sample_start_index"] + len(previous["samples"])
                                       + chunk["dropped_samples_before"]):
        raise ValueError("sample_discontinuity")
    if chunk["device_epoch"] == previous["device_epoch"]:
        if chunk["device_times_s"][0] <= previous["device_times_s"][-1]:
            raise ValueError("stale_device_time")
    a, b = previous["host_receipt"], chunk["host_receipt"]
    if a["epoch"] == b["epoch"] and b["seconds"] < a["seconds"]:
        raise ValueError("host_time_reversal")


class Recorder:
    def __init__(self, path: Path, metadata: dict, *, explicitly_started: bool):
        validate(metadata)
        if metadata["kind"] != "AcquisitionMetadata" or not explicitly_started:
            raise ValueError("visible_explicit_start_required")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", metadata["session_id"]):
            raise ValueError("pseudonymous_session_id_required")
        self.path, self.metadata, self.previous = Path(path), metadata, None
        self.closed = False
        self.path.mkdir(parents=True, exist_ok=False, mode=0o700)
        (self.path / "chunks").mkdir(mode=0o700)
        atomic(self.path / "manifest.json", {"format": FORMAT, "status": "recording", "metadata": metadata,
               "timing": "device/source times preserved; host receipt is batch arrival, never sample occurrence",
               "hardware_status": "operator_verified" if metadata["hardware_verified"] else "HARDWARE_UNVERIFIED"})

    def append(self, chunk):
        if self.closed:
            raise ValueError("recorder_closed")
        validate(chunk)
        if chunk["kind"] != "EEGChunk" or not 0 < len(chunk["samples"]) <= MAX_SAMPLES:
            raise ValueError("invalid_or_oversized_chunk")
        if len(encoded(chunk)) > MAX_CHUNK_BYTES:
            raise ValueError("record_too_large")
        for field in ("session_id", "channels", "sample_rate_hz"):
            if chunk[field] != self.metadata[field]:
                raise ValueError("metadata_mismatch:" + field)
        if chunk["provenance"]["source_mode"] != self.metadata["provenance"]["source_mode"]:
            raise ValueError("source_mode_mismatch")
        check_pair(self.previous, chunk)
        atomic(self.path / "chunks" / f'{chunk["sequence"]:09d}.json', chunk)
        self.previous = chunk

    def close(self, reason="user_stop"):
        manifest = read_json(self.path / "manifest.json")
        manifest.update(status="closed", stop_reason=reason,
                        committed_chunks=0 if self.previous is None else self.previous["sequence"] + 1)
        atomic(self.path / "manifest.json", manifest)
        self.closed = True


def manifest(path):
    root = Path(path)
    if root.is_symlink() or (root / "manifest.json").is_symlink():
        raise ValueError("symlink_session")
    value = read_json(root / "manifest.json")
    if value.get("format") != FORMAT:
        raise ValueError("not_a_raw_session")
    validate(value["metadata"])
    return value


def replay(path):
    """Exact numerical/clock replay, lazy per chunk. Provenance never rewritten."""
    root, previous = Path(path), None
    meta = manifest(root)["metadata"]
    if (root / "chunks").is_symlink():
        raise ValueError("symlink_chunks")
    for file in sorted((root / "chunks").glob("*.json")):
        if file.is_symlink():
            raise ValueError("symlink_chunk")
        chunk = read_json(file)
        validate(chunk)
        if chunk["kind"] != "EEGChunk" or not 0 < len(chunk["samples"]) <= MAX_SAMPLES:
            raise ValueError("invalid_chunk")
        if file.name != f'{chunk["sequence"]:09d}.json':
            raise ValueError("chunk_name_mismatch")
        for field in ("session_id", "channels", "sample_rate_hz"):
            if chunk[field] != meta[field]:
                raise ValueError("metadata_mismatch:" + field)
        if chunk["provenance"]["source_mode"] != meta["provenance"]["source_mode"]:
            raise ValueError("source_mode_mismatch")
        check_pair(previous, chunk)
        previous = chunk
        yield chunk


def recover(path):
    """Index all atomically committed chunks; ignore interrupted *.tmp writes."""
    value = manifest(path)
    count = sum(1 for _ in replay(path))
    value.update(status="recovered", committed_chunks=count, stop_reason="interrupted_recording")
    atomic(Path(path) / "manifest.json", value)
    return value


def export_session(path, destination):
    root, destination = Path(path).resolve(), Path(destination).resolve()
    manifest(root)
    if destination.is_relative_to(root):
        raise ValueError("export_must_be_outside_session")
    list_checks = sum(1 for _ in replay(root))
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        os.chmod(destination, 0o600)
        for file in sorted(root.rglob("*")):
            if file.is_symlink():
                raise ValueError("symlink_export")
            if file.is_file() and not file.name.endswith(".tmp"):
                archive.write(file, file.relative_to(root))
    return {"chunks": list_checks, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "privacy": "local_export_contains_raw_EEG_and_labels"}


def delete_session(path, *, confirmed_session_id):
    root = Path(path)
    value = manifest(root)
    if value["metadata"]["session_id"] != confirmed_session_id:
        raise ValueError("session_confirmation_mismatch")
    shutil.rmtree(root)
