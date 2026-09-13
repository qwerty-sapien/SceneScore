"""Local source/recorder lifecycle. Training never holds the acquisition lock."""

from collections import deque
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import threading
import time

from modules.muse.acquisition.store import Recorder, atomic, encoded, manifest, replay
from .sources import Sources
from .storage import RawCache
from .diagnostics import Diagnostics

VERSION = "muse-training-1"
CLASSES = {"double", "single", "triple", "natural", "artifact", "keypress_only"}
MAX_EXPORT = 32 * 1024 * 1024


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise ValueError("bounded_path_safe_identifier_required")
    return value


def text(value, length=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > length:
        raise ValueError("bounded_nonempty_text_required")
    return value.strip()


def read_lines(path):
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > MAX_EXPORT:
        raise ValueError("invalid_or_oversized_local_file")
    return [json.loads(line) for line in path.read_text().splitlines()]


def append(path, value):
    if path.is_symlink():
        raise ValueError("symlink_local_file")
    with path.open("ab") as stream:
        stream.write(encoded(value))


class Workspace:
    def __init__(self, data_root, *, sources=None, trainer=None, predictor=None, subscriber_timeout=5):
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.sources = sources or Sources()
        self.trainer, self.predictor = trainer, predictor
        self.lock = threading.RLock()
        self.generation = 0
        self.worker = None
        self.stop_event = threading.Event()
        self.connected = self.connecting = self.training = self.closed = False
        self.mode = self.source = self.metadata = None
        self.reason, self.quality = "Select a source to begin", "unverified"
        self.rows = deque(maxlen=8192)
        self.sample_count, self.last_device_s, self.last_host_s = 0, None, None
        self.measured_rate_hz = None
        self.last_subscriber = time.monotonic()
        self.subscriber_timeout = subscriber_timeout
        self.recorder = None
        self.current_session_id = None
        self.record_deadline = 0
        self.record_index = self.record_sequence = self.record_bytes = 0
        self.record_previous = None
        self.host_epoch = "training-host-" + secrets.token_hex(8)
        self.model = None
        self.model_revision = 0
        self.records = {}
        self.raw_cache = RawCache()
        self.diagnostics = Diagnostics(self)
        from .automatic import AutomaticTrainer
        self.automatic = AutomaticTrainer(self.root / "automatic", self.sources)
        for path in sorted(self.root.glob("session-*")):
            if len(self.records) >= 64:
                raise ValueError("session_capacity_exceeded")
            if path.is_symlink():
                raise ValueError("symlink_session")
            if (path / "session.json").is_file():
                value = json.loads((path / "session.json").read_text())
                if value["status"] == "recording":
                    chunks = list(replay(path))
                    value["samples"] = sum(len(c["samples"]) for c in chunks)
                    value["start_s"] = chunks[0]["device_times_s"][0] if chunks else None
                    value["end_s"] = chunks[-1]["device_times_s"][-1] if chunks else None
                    value["duration_s"] = (
                        value["end_s"] - value["start_s"] + 1 / chunks[0]["sample_rate_hz"] if chunks else 0
                    )
                    value["status"] = "closed" if chunks else "empty"
                    value["stop_reason"] = "recovered_interrupted_recording"
                    value["marker_count"] = len({m["id"] for m in read_lines(path / "markers.jsonl")})
                    atomic(path / "session.json", value)
                self.records[value["id"]] = value
        if (self.root / "model.json").is_file():
            self.model = json.loads((self.root / "model.json").read_text())

    def touch(self):
        with self.lock:
            self.last_subscriber = time.monotonic()

    def status(self):
        with self.lock:
            return {
                "version": VERSION,
                "connected": self.connected,
                "connecting": self.connecting,
                "mode": self.mode,
                "recording": self.recorder is not None,
                "source": self.source,
                "channels": []
                if not self.metadata
                else [{"name": c["name"], "unit": c["unit"]} for c in self.metadata["channels"]],
                "sample_rate_hz": None if not self.metadata else self.metadata["sample_rate_hz"],
                "measured_rate_hz": self.measured_rate_hz,
                "sample_count": self.sample_count,
                "last_device_s": self.last_device_s,
                "sample_age_s": None if self.last_host_s is None else max(0, time.monotonic() - self.last_host_s),
                "device_epoch": None if not self.metadata else self.metadata["clock_epoch"],
                "quality": self.quality,
                "reason": self.reason,
                "current_session_id": self.current_session_id,
                "sessions": copy.deepcopy(list(self.records.values())),
                "model": self.model_summary(),
                "training": self.training,
            }

    def model_summary(self):
        if self.model is None:
            return None
        keys = (
            "id",
            "status",
            "positive_examples",
            "negative_examples",
            "source_mode",
            "held_out",
            "model_kind",
            "control_authority",
        )
        return {key: self.model.get(key) for key in keys}

    def connect(self, body):
        if self.automatic.status()["active"]:
            raise ValueError("stop_automatic_training_before_manual_connection")
        if body.get("consent") is not True:
            raise ValueError("explicit_live_processing_consent_required")
        source_id, device_model = text(body.get("source_id"), 256), text(body.get("device_model"), 100)
        with self.lock:
            if self.closed or self.worker is not None or self.connecting:
                raise ValueError("disconnect_before_connecting")
            self.generation += 1
            generation = self.generation
            self.connecting = True
        source = None
        try:
            source = self.sources.open(source_id)
            d = source.description
            mode = "synthetic" if source_id == "synthetic" else "real_device"
            metadata = {
                "kind": "AcquisitionMetadata",
                "schema_version": "0.1",
                "id": "training-metadata-" + secrets.token_hex(8),
                "session_id": "preview-" + secrets.token_hex(8),
                "device_model": device_model,
                "transport": "fixture" if mode == "synthetic" else "lsl",
                "sample_rate_hz": d["sample_rate_hz"],
                "channels": [{**c, "enabled": True} for c in d["channels"]],
                "clock_epoch": mode + "-" + secrets.token_hex(8),
                "hardware_verified": False,
                "raw_storage": "local_only",
                "provenance": {
                    "source_mode": mode,
                    "creator": VERSION,
                    "tool_version": VERSION,
                    "config_hash": hashlib.sha256(encoded(d)).hexdigest(),
                    "input_hashes": [],
                    "seed": 1 if mode == "synthetic" else None,
                },
            }
            with self.lock:
                if generation != self.generation:
                    raise ValueError("connect_cancelled")
                self.metadata, self.mode, self.source = metadata, mode, copy.deepcopy(d)
                self.rows.clear()
                self.sample_count, self.last_device_s, self.last_host_s = 0, None, None
                self.measured_rate_hz = None
                self.connected, self.connecting = True, False
                self.reason, self.quality = "Waiting for source samples; contact quality unverified", "unverified"
                self.last_subscriber = time.monotonic()
                self.stop_event = threading.Event()
                self.worker = threading.Thread(
                    target=self._run,
                    args=(source, generation, self.stop_event),
                    name="muse-training-source",
                    daemon=False,
                )
                self.worker.start()
                source = None  # ownership transferred to worker
            return self.status()
        finally:
            if source is not None:
                source.close()
            with self.lock:
                if generation == self.generation:
                    self.connecting = False

    def _run(self, source, generation, stop):
        reason, last_received = "disconnected", time.monotonic()
        buffered_rows, buffered_times = [], []
        try:
            while not stop.is_set():
                if time.monotonic() - self.last_subscriber > self.subscriber_timeout:
                    reason = "browser_subscriber_timeout"
                    break
                rows, times = source.pull()
                now = time.monotonic()
                with self.lock:
                    if generation != self.generation:
                        break
                    if self.recorder is not None and now >= self.record_deadline:
                        self._stop_record("duration_limit")
                if not times:
                    if now - last_received > 2:
                        reason = "source_timeout"
                        break
                    continue
                last_received = now
                buffered_rows.extend(rows)
                buffered_times.extend(times)
                while len(buffered_times) >= 32:
                    size = min(128, len(buffered_times))
                    self.consume(buffered_rows[:size], buffered_times[:size], now)
                    del buffered_rows[:size]
                    del buffered_times[:size]
        except Exception as exc:
            reason = "source_fault:" + str(exc)
        finally:
            try:
                with self.lock:
                    if generation == self.generation and buffered_times:
                        try:
                            self.consume(buffered_rows, buffered_times, time.monotonic())
                        except Exception:
                            reason = "source_fault_in_final_batch"
                source.close()
            finally:
                with self.lock:
                    try:
                        if generation == self.generation:
                            self._stop_record(reason)
                    except Exception as exc:
                        reason = "recording_persistence_fault:" + str(exc)
                    finally:
                        if generation == self.generation:
                            self.connected = False
                            self.quality, self.reason = "unverified", reason
                        if self.worker is threading.current_thread():
                            self.worker = None

    def consume(self, rows, times, host_s):
        if not times or len(rows) != len(times) or len(times) > 128:
            raise ValueError("source_batch_dimension")
        with self.lock:
            if self.metadata is None:
                raise ValueError("source_not_connected")
            rate, count = self.metadata["sample_rate_hz"], len(self.metadata["channels"])
            previous = self.last_device_s
            for row, timestamp in zip(rows, times):
                if (
                    len(row) != count
                    or any(not math.isfinite(x) for x in row)
                    or not math.isfinite(timestamp)
                    or timestamp < 0
                ):
                    raise ValueError("invalid_raw_sample")
                if previous is not None and timestamp <= previous:
                    raise ValueError("source_timestamp_reset_reconnect_required")
                previous = timestamp
            # Split at every source gap; preserve each raw sample and source timestamp.
            groups, current, current_times, prev = [], [], [], self.last_device_s
            for row, timestamp in zip(rows, times):
                if prev is not None and timestamp - prev > 1.5 / rate and current:
                    groups.append((current, current_times))
                    current, current_times = [], []
                self.rows.append((timestamp, list(row), prev is not None and timestamp - prev > 1.5 / rate))
                current.append(list(row))
                current_times.append(timestamp)
                prev = timestamp
            if current:
                groups.append((current, current_times))
            self.sample_count += len(times)
            self.last_device_s, self.last_host_s = times[-1], host_s
            self.quality = "good" if self.mode == "synthetic" else "unverified"
            self.reason = (
                "Synthetic rehearsal; no hardware claim"
                if self.mode == "synthetic"
                else "Live samples; contact quality unverified; no music authority"
            )
            if len(self.rows) >= 256:
                tail = list(self.rows)[-256:]
                self.measured_rate_hz = (
                    None if any(x[2] for x in tail[1:]) else (len(tail) - 1) / (tail[-1][0] - tail[0][0])
                )
            if self.recorder is not None:
                for data, timestamps in groups:
                    if self.recorder is None:
                        break
                    gap = (
                        0
                        if self.record_previous is None
                        else max(0, round((timestamps[0] - self.record_previous) * rate) - 1)
                    )
                    metadata = self.recorder.metadata
                    chunk = {
                        "kind": "EEGChunk",
                        "schema_version": "0.1",
                        "id": metadata["session_id"] + f"-{self.record_sequence}",
                        "session_id": metadata["session_id"],
                        "provenance": metadata["provenance"],
                        "sequence": self.record_sequence,
                        "sample_start_index": self.record_index + gap,
                        "sample_rate_hz": rate,
                        "channels": metadata["channels"],
                        "device_times_s": timestamps,
                        "device_epoch": metadata["clock_epoch"],
                        "host_receipt": {"seconds": host_s, "clock": "host_monotonic", "epoch": self.host_epoch},
                        "samples": data,
                        "dropped_samples_before": gap,
                        "quality": {
                            "state": self.quality,
                            "reason": None if self.mode == "synthetic" else "contact_quality_unverified",
                        },
                        "imu": None,
                    }
                    size = len(encoded(chunk))
                    if self.record_bytes + size > MAX_EXPORT - 1024 * 1024:
                        self._stop_record("local_storage_capacity_limit")
                        break
                    self.recorder.append(chunk)
                    self.record_bytes += size
                    self.record_sequence += 1
                    self.record_index += gap + len(data)
                    self.record_previous = timestamps[-1]
                    record = self.records[self.current_session_id]
                    record["samples"] += len(data)
                    record["start_s"] = timestamps[0] if record["start_s"] is None else record["start_s"]
                    record["end_s"] = timestamps[-1]
                    record["duration_s"] = record["end_s"] - record["start_s"] + 1 / rate

    def disconnect(self):
        error = None
        with self.lock:
            self.generation += 1
            self.stop_event.set()
            worker = self.worker
            try:
                self._stop_record("user_disconnect")
            except Exception as exc:
                error = exc
            finally:
                self.connected = self.connecting = False
                self.reason = "Disconnected" if error is None else "recording_persistence_fault:" + str(error)
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=3)
            if worker.is_alive():
                raise RuntimeError("source_shutdown_incomplete")
        if error is not None:
            raise RuntimeError("recording_persistence_fault:" + str(error))
        return self.status()

    def automatic_start(self, body):
        with self.lock:
            if self.recorder is not None or self.training:
                raise ValueError("stop_manual_recording_or_training_first")
        if self.connected:
            self.disconnect()
        return self.automatic.start(body)

    def record_start(self, body):
        participant, refit = identifier(body.get("participant_id")), identifier(body.get("refit_id"))
        role, seconds = body.get("role"), body.get("seconds")
        if (
            role not in {"train", "development", "final_test"}
            or not isinstance(seconds, (float, int))
            or not math.isfinite(seconds)
            or not 10 <= seconds <= 600
        ):
            raise ValueError("role_and_10_to_600_second_budget_required")
        if body.get("consent") is not True:
            raise ValueError("separate_local_recording_consent_required")
        statement = text(body.get("consent_statement"), 2000)
        with self.lock:
            if (
                self.closed
                or not self.connected
                or self.last_device_s is None
                or self.recorder is not None
                or self.training
            ):
                raise ValueError("connected_samples_and_idle_recorder_required")
            if len(self.records) >= 64:
                raise ValueError("session_capacity_exceeded")
            if any(
                s["participant_id"] == participant and s["refit_id"] == refit and s["role"] != role
                for s in self.records.values()
            ):
                raise ValueError("refit_split_leakage")
            if self.mode == "real_device" and (
                body.get("metadata_confirmed") is not True
                or self.measured_rate_hz is None
                or abs(self.measured_rate_hz / self.metadata["sample_rate_hz"] - 1) > 0.02
            ):
                raise ValueError("real_recording_requires_metadata_attestation_and_consistent_observed_rate")
            sid = "session-" + secrets.token_hex(10)
            meta = copy.deepcopy(self.metadata)
            meta.update(session_id=sid, id="metadata-" + sid, hardware_verified=self.mode == "real_device")
            self.recorder = Recorder(self.root / sid, meta, explicitly_started=True)
            self.current_session_id = sid
            self.record_index = self.record_sequence = self.record_bytes = 0
            self.record_previous = None
            self.record_deadline = time.monotonic() + seconds
            self.records[sid] = {
                "id": sid,
                "participant_id": participant,
                "refit_id": refit,
                "role": role,
                "source_mode": self.mode,
                "samples": 0,
                "duration_s": 0,
                "marker_count": 0,
                "reviewed_count": 0,
                "status": "recording",
                "start_s": None,
                "end_s": None,
            }
            atomic(self.root / sid / "session.json", self.records[sid])
            atomic(
                self.root / sid / "consent.json",
                {
                    "statement": statement,
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "local_only": True,
                    "publication_consent": False,
                    "seconds_limit": seconds,
                    "device_model_attestation": meta["device_model"],
                    "source_descriptor": self.source,
                    "metadata_verification_scope": "Explicit operator attestation of named device/selected descriptor plus source-timestamp rate consistency; no physical/contact-quality measurement",
                    "metadata_confirmed": body.get("metadata_confirmed") is True,
                },
            )
        return self.status()

    def _stop_record(self, reason):
        if self.recorder is None:
            return
        recorder, sid = self.recorder, self.current_session_id
        self.recorder = None
        record = self.records[sid]
        record["stop_reason"] = reason
        try:
            for marker in self.markers(sid):
                if marker["end_s"] is None or (record["end_s"] is not None and marker["end_s"] > record["end_s"]):
                    append(
                        self.root / sid / "markers.jsonl",
                        {
                            **marker,
                            "end_s": record["end_s"],
                            "closed_reason": reason,
                            "host_end_s": time.monotonic(),
                            "revision": marker.get("revision", 0) + 1,
                        },
                    )
            recorder.close(reason)
            record["status"] = "closed" if record["samples"] else "empty"
            atomic(self.root / sid / "session.json", record)
        except Exception:
            record["status"] = "interrupted"
            raise

    def record_stop(self):
        with self.lock:
            self._stop_record("user_stop")
        return self.status()

    def path(self, sid):
        identifier(sid)
        if sid not in self.records or (self.root / sid).is_symlink():
            raise ValueError("unknown_session")
        return self.root / sid

    def markers(self, sid):
        latest = {}
        for marker in read_lines(self.path(sid) / "markers.jsonl"):
            latest[marker["id"]] = marker
        return list(latest.values())

    def marker(self, body):
        marker_id, kind, class_name = identifier(body.get("id")), body.get("event"), body.get("class_name")
        client = body.get("client_ms")
        if (
            kind not in {"down", "up", "cue"}
            or class_name not in CLASSES
            or not isinstance(client, (int, float))
            or not math.isfinite(client)
        ):
            raise ValueError("invalid_marker")
        with self.lock:
            if self.recorder is None or self.last_device_s is None:
                raise ValueError("record_before_marking")
            sid = self.current_session_id
            existing = {m["id"]: m for m in self.markers(sid)}
            if kind in {"down", "cue"} and marker_id in existing:
                return existing[marker_id]
            if len(existing) >= 500 and marker_id not in existing:
                raise ValueError("marker_capacity_exceeded")
            now = time.monotonic()
            if kind == "up":
                if marker_id not in existing:
                    raise ValueError("marker_down_missing")
                value = existing[marker_id]
                if value["end_s"] is not None:
                    return value
                value = {
                    **value,
                    "end_s": self.last_device_s,
                    "browser_end_ms": client,
                    "host_end_s": now,
                    "revision": 1,
                }
            else:
                value = {
                    "id": marker_id,
                    "class_name": class_name,
                    "start_s": self.last_device_s,
                    "end_s": self.last_device_s + 2 if kind == "cue" else None,
                    "source": "guided_cue" if kind == "cue" else "keyboard_intent",
                    "review_required": True,
                    "browser_start_ms": client,
                    "host_start_s": now,
                    "device_epoch": self.metadata["clock_epoch"],
                    "source_anchor_s": self.last_device_s,
                    "anchor_host_receipt_s": self.last_host_s,
                    "anchor_age_s": now - self.last_host_s,
                    "clock_mapping_uncertainty_s": None,
                    "is_ground_truth": False,
                    "timing_note": "Latest source-batch anchor; no calibrated browser-to-device clock mapping",
                    "revision": 0,
                }
            append(self.root / sid / "markers.jsonl", value)
            self.records[sid]["marker_count"] = len(existing) + (marker_id not in existing)
            return value

    def review_get(self, sid):
        with self.lock:
            path = self.path(sid)
            return {
                "session": copy.deepcopy(self.records[sid]),
                "markers": self.markers(sid),
                "reviews": read_lines(path / "reviews.jsonl"),
            }

    def review(self, body):
        sid, marker_id = identifier(body.get("session_id")), identifier(body.get("marker_id"))
        start, end = body.get("start_s"), body.get("end_s")
        if (
            any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in (start, end))
            or not 0 <= start < end
            or end - start > 10
        ):
            raise ValueError("bounded_device_review_interval_required")
        if body.get("class_name") not in CLASSES or body.get("certainty") not in {"reviewed", "uncertain"}:
            raise ValueError("review_class_and_certainty_required")
        reviewer = text(body.get("reviewer"), 100)
        notes = body.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError("bounded_notes_required")
        with self.lock:
            path = self.path(sid)
            record = self.records[sid]
            if record["status"] != "closed" or self.recorder is not None:
                raise ValueError("review_only_after_recording_stops")
            if start < record["start_s"] or end > record["end_s"]:
                raise ValueError("review_outside_recorded_device_bounds")
            if marker_id not in {m["id"] for m in self.markers(sid)}:
                raise ValueError("unknown_marker")
            old = read_lines(path / "reviews.jsonl")
            if len(old) >= 1000:
                raise ValueError("review_capacity_exceeded")
            value = {
                "id": "review-" + secrets.token_hex(8),
                "marker_id": marker_id,
                "start_s": start,
                "end_s": end,
                "class_name": body["class_name"],
                "certainty": body["certainty"],
                "reviewer": reviewer,
                "notes": notes,
                "source": "reviewer_adjusted_raw_trace_review",
                "device_epoch": manifest(path)["metadata"]["clock_epoch"],
                "supersedes": next((v["id"] for v in reversed(old) if v["marker_id"] == marker_id), None),
            }
            append(path / "reviews.jsonl", value)
            record["reviewed_count"] = len({v["marker_id"] for v in old + [value]})
            atomic(path / "session.json", record)
            self.model_revision += 1
            self.model = None
            (self.root / "model.json").unlink(missing_ok=True)
            return value

    def trace(self):
        with self.lock:
            data = list(self.rows)
            if data:
                data = [r for r in data if r[0] >= data[-1][0] - 10]
            metadata, source, model, generation = (
                copy.deepcopy(self.metadata),
                copy.deepcopy(self.source),
                self.model,
                self.generation,
            )
            connected = self.connected
        result = self._trace(data, metadata, source)
        if not connected or model is None or not data:
            return result
        indices = source["frontal_indices"]
        contract = [
            [(metadata["channels"][i]["name"], metadata["channels"][i]["unit"]) for i in indices],
            metadata["sample_rate_hz"],
            metadata["provenance"]["source_mode"],
        ]
        if encoded(contract) != encoded(model.get("channel_contract")):
            result["prediction_reason"] = "model_source_channel_or_rate_mismatch"
            return result
        try:
            predictor = self.predictor
            if predictor is None:
                from modules.muse.training.web_model import predict_window

                predictor = predict_window
            window = [row for row in data if row[0] >= data[-1][0] - 2 - 1 / metadata["sample_rate_hz"]]
            if any(row[2] for row in window[1:]):
                raise ValueError("gapped_prediction_window")
            score = predictor(
                model,
                [row[0] for row in window],
                [[row[1][i] for i in indices] for row in window],
                metadata["sample_rate_hz"],
            )
            with self.lock:
                if generation == self.generation and model is self.model and self.connected:
                    result["prediction"] = {
                        "score": score,
                        "model_id": model["id"],
                        "semantics": "Experimental personal 2-second window score; uncalibrated; no music authority",
                    }
        except (ValueError, ImportError) as exc:
            result["prediction_reason"] = str(exc)
        return result

    @staticmethod
    def _trace(data, metadata, source):
        if metadata is None:
            return {
                "channels": [],
                "times_s": [],
                "samples": [],
                "device_epoch": None,
                "source_mode": None,
                "quality": "unverified",
                "prediction": None,
                "gaps": [],
            }
        stride = max(1, math.ceil(len(data) / 2048))
        shown = data[::stride]
        indices = source["frontal_indices"]
        return {
            "channels": [
                {"name": metadata["channels"][i]["name"], "unit": metadata["channels"][i]["unit"]} for i in indices
            ],
            "times_s": [r[0] for r in shown],
            "samples": [[r[1][i] for i in indices] for r in shown],
            "device_epoch": metadata["clock_epoch"],
            "source_mode": metadata["provenance"]["source_mode"],
            "quality": "good" if metadata["provenance"]["source_mode"] == "synthetic" else "unverified",
            "prediction": None,
            "gaps": [r[0] for r in data if r[2]],
            "decimation_stride": stride,
        }

    def raw(self, sid):
        path = self.path(sid)
        if self.records[sid]["status"] != "closed":
            raise ValueError("stop_recording_before_raw_review_or_export")
        raw = self.raw_cache.read(path)
        return {**raw, "markers": self.markers(sid), "reviews": read_lines(path / "reviews.jsonl")}

    def segment(self, sid, start, end):
        if not all(math.isfinite(x) for x in (start, end)) or not 0 <= start < end or end - start > 10:
            raise ValueError("segment_maximum_10_seconds")
        with self.lock:
            self.path(sid)
            if self.records[sid]["status"] != "closed":
                raise ValueError("stop_recording_before_review")
        raw = self.raw(sid)
        meta = raw["metadata"]
        d = raw["consent"]["source_descriptor"]
        data = [
            (t, r, bool(c["dropped_samples_before"] and i == 0))
            for c in raw["chunks"]
            for i, (t, r) in enumerate(zip(c["device_times_s"], c["samples"]))
            if start <= t <= end
        ]
        if not data:
            raise ValueError("segment_outside_recorded_data")
        result = self._trace(data, meta, d)
        result["reviews"] = raw["reviews"]
        return result

    def train(self):
        with self.lock:
            if self.recorder is not None or self.training:
                raise ValueError("stop_recording_before_training")
            self.training = True
            revision = self.model_revision
            sessions = copy.deepcopy(list(self.records.values()))
        try:
            examples, contract, excluded = [], None, []
            for session in sessions:
                if session["status"] != "closed" or session["role"] == "final_test":
                    continue
                raw = self.raw(session["id"])
                meta = raw["metadata"]
                indices = raw["consent"]["source_descriptor"]["frontal_indices"]
                channel_contract = [(meta["channels"][i]["name"], meta["channels"][i]["unit"]) for i in indices]
                current = (channel_contract, meta["sample_rate_hz"], session["source_mode"])
                latest = {v["marker_id"]: v for v in raw["reviews"]}
                for review in latest.values():
                    if review["certainty"] != "reviewed":
                        excluded.append(review["id"])
                        continue
                    if contract is not None and current != contract:
                        raise ValueError("consistent_channel_order_units_rate_source_mode_required")
                    contract = current
                    if len(examples) >= 128:
                        raise ValueError("training_example_capacity_exceeded")
                    rows, times = [], []
                    for c in raw["chunks"]:
                        if c["device_epoch"] != review["device_epoch"]:
                            raise ValueError("epoch_mismatch_in_training_window")
                        for t, row in zip(c["device_times_s"], c["samples"]):
                            if review["end_s"] - 2 - 1 / meta["sample_rate_hz"] <= t <= review["end_s"]:
                                times.append(t)
                                rows.append([row[i] for i in indices])
                    if (
                        len(times) < 2
                        or times[0] > review["end_s"] - 2 + 1 / meta["sample_rate_hz"]
                        or any(b - a > 1.5 / meta["sample_rate_hz"] for a, b in zip(times, times[1:]))
                    ):
                        raise ValueError("two_seconds_contiguous_preceding_data_required")
                    examples.append(
                        {
                            "session_id": session["id"],
                            "participant_id": session["participant_id"],
                            "refit_id": session["refit_id"],
                            "role": session["role"],
                            "source_mode": session["source_mode"],
                            "review_id": review["id"],
                            "certainty": "reviewed",
                            "class_name": review["class_name"],
                            "times_s": times,
                            "samples": rows,
                            "sample_rate_hz": meta["sample_rate_hz"],
                            "start_s": review["start_s"],
                            "end_s": review["end_s"],
                        }
                    )
            trainer = self.trainer
            if trainer is None:
                from modules.muse.training.web_model import train_model

                trainer = train_model
            result = trainer(examples)
            result["report"]["backend_excluded_uncertain_review_ids"] = excluded
            with self.lock:
                if revision != self.model_revision:
                    raise ValueError("reviews_changed_during_training_retry")
                result["model"]["channel_contract"] = contract
                atomic(self.root / "model.json", result["model"])
                self.model = result["model"]
                return {"model": self.model_summary(), "report": result["report"]}
        finally:
            with self.lock:
                self.training = False

    def delete(self, body):
        sid = identifier(body.get("session_id"))
        if sid != body.get("confirmed_session_id"):
            raise ValueError("exact_session_delete_confirmation_required")
        with self.lock:
            if self.recorder is not None or self.training:
                raise ValueError("stop_recording_and_training_before_deleting")
            path = self.path(sid)
            from modules.muse.acquisition.store import delete_session

            delete_session(path, confirmed_session_id=sid)
            self.raw_cache.invalidate(path)
            del self.records[sid]
            self.model = None
            self.model_revision += 1
            (self.root / "model.json").unlink(missing_ok=True)
            if self.current_session_id == sid:
                self.current_session_id = None
        return self.status()

    def close(self):
        with self.lock:
            self.closed = True
            self.model_revision += 1
        try:
            self.diagnostics.close()
        finally:
            try:
                self.automatic.close()
            finally:
                self.disconnect()
