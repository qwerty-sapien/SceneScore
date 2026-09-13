"""Explicit-start B-labelled local trainer, immutable checkpoints and fresh checks.

This format records reported labels and observed descriptors without promoting
them to the independently reviewed, hardware-verified contract 0.1 dataset.
"""
from __future__ import annotations

from collections import deque
import copy
import json
import math
from pathlib import Path
import secrets
import threading
import time

from modules.muse.baseline.causal import Config
from modules.muse.training.checkpoints import (
    CheckpointStore, atomic_json, fit_checkpoint, training_batch,
)
from modules.muse.training.personal_detector import PersonalDetector
from modules.muse.training.web_model import _features, _digest

FORMAT = "scenescore.automatic-blink-run/1"
CONSENT = "Train records EEG and B labels on this machine and trains a personal model locally. No upload."
ACTIVE = {"connecting", "learning", "fitting", "checking", "stopping"}
MAX_RAW = 32 * 1024 * 1024


def union_seconds(intervals, start, end):
    total, last = 0.0, start
    for left, right in sorted(intervals):
        left, right = max(start, left), min(end, right)
        if right > max(left, last):
            total += right - max(left, last)
            last = right
    return total


def check_metrics(labels, decisions, *, elapsed_s, usable_s, background_s, complete=False):
    """Reported B timing only; never manufacture independently verified events."""
    used, pairs, false = set(), [], []
    for event in sorted(decisions, key=lambda v: (v["decision_s"], v["id"])):
        eligible = [b for b in labels if b["id"] not in used
                    and b["epoch"] == event["epoch"]
                    and b["source_s"] - 1 <= event["final_blink_s"] <= b["source_s"] + .25]
        if eligible:
            label = min(eligible, key=lambda b: (abs(b["source_s"] - event["final_blink_s"]), b["source_s"], b["id"]))
            used.add(label["id"])
            pairs.append({"label_id": label["id"], "decision_id": event["id"]})
        else:
            false.append(event["id"])
    tp, fp, fn = len(pairs), len(false), len(labels) - len(pairs)
    precision, recall = tp / (tp + fp) if tp + fp else None, tp / len(labels) if labels else None
    availability = min(1.0, usable_s / elapsed_s) if elapsed_s > 0 else 0.0
    enough = len(labels) >= 30 and elapsed_s >= 120 and background_s >= 60
    return {"semantics": "agreement_with_B_labels_not_independent_blink_accuracy", "complete": bool(complete and enough),
            "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "labels": len(labels), "monitored_s": elapsed_s, "usable_s": usable_s,
            "background_s": background_s, "availability": availability,
            "target_reached": bool(complete and enough and precision is not None and recall is not None
                                   and precision > .93 and recall > .93 and availability >= .95),
            "target_advisory": True, "production_accuracy_gate": False,
            "pairs": pairs, "unmatched_decisions": false,
            "unmatched_labels": [b["id"] for b in labels if b["id"] not in used],
            "matcher": {"before_B_s": 1.0, "after_B_s": .25, "one_to_one": True}}


class AutomaticTrainer:
    def __init__(self, root, sources, *, synthetic=False, clock=time.monotonic):
        self.root = Path(root)
        self.store = CheckpointStore(self.root)
        self.sources, self.synthetic, self.clock = sources, synthetic, clock
        self.lock = threading.RLock()
        self.thread = self.fit_thread = None
        self.cancel = threading.Event()
        self.closed = False
        self.phase, self.message = "idle", "Ready to train."
        self.run = None
        self.checkpoint = None
        self.evaluation = None
        self.source = None
        self.fit_error = None
        self.fit_result = None
        self.labels = []
        self.rows = deque(maxlen=16384)
        self.learning = []
        self.stage = 0
        self.stage_start = 0.0
        self.stage_label_start = 0
        self.stage_new = [0, 0]
        self.check_decisions = []
        self.usable_intervals = []
        self.byte_count = 0
        self.last_source_s = self.last_sample_host = None
        self.subscriber_s = clock()
        self.started = 0.0
        self.stopped = None
        self.last_negative_end = -math.inf
        self.sequence = self.sample_index = 0
        self.detector = None
        self.check_started_host = 0.0
        self.check_started_source = 0.0
        self.failure = False
        self.path = None

    def touch(self):
        with self.lock:
            self.subscriber_s = self.clock()

    def status(self):
        with self.lock:
            cp = self.checkpoint
            return {"format": FORMAT, "phase": self.phase, "active": self.phase in ACTIVE,
                    "message": self.message, "run_id": self.run["id"] if self.run else None,
                    "source_mode": "synthetic" if self.synthetic else "real_device",
                    "elapsed_s": max(0, (self.stopped if self.stopped is not None else self.clock()) - self.started) if self.run else 0,
                    "limit_s": 600, "labels": len(self.labels),
                    "usable_positive_windows": sum(e["label"] for e in self.learning),
                    "background_windows": sum(1 - e["label"] for e in self.learning),
                    "checkpoint_id": cp["id"] if cp else None,
                    "training_steps": cp["training_steps"] if cp else 0,
                    "evaluation": self.evaluation, "target": .93, "target_advisory": True}

    def start(self, body):
        if body != {"consent": True}:
            raise ValueError("explicit_Train_local_recording_consent_required")
        with self.lock:
            if self.closed or (self.thread and self.thread.is_alive()) or self.phase in ACTIVE:
                raise ValueError("automatic_run_already_active_or_closed")
            self.cancel = threading.Event()
            self.started, self.stopped, self.subscriber_s = self.clock(), None, self.clock()
            self.phase, self.message = "connecting", "Connecting to your EEG source…"
            self.labels, self.learning, self.check_decisions, self.usable_intervals = [], [], [], []
            self.rows.clear()
            self.stage_new, self.stage_label_start, self.stage = [0, 0], 0, 0
            self.last_source_s = self.last_sample_host = None
            self.sequence = self.sample_index = self.byte_count = 0
            self.last_negative_end = -math.inf
            self.fit_result = self.fit_error = None
            self.failure, self.checkpoint, self.evaluation, self.detector = False, None, None, None
            self.run = {"format": FORMAT, "id": "run-" + str(time.time_ns()) + "-" + secrets.token_hex(4),
                        "created_ns": time.time_ns(), "consent": CONSENT, "consent_action": "Train",
                        "raw_storage": "local_only", "hardware_verified": False,
                        "participant": "local-owner", "refit_status": "unknown_not_independent",
                        "source_mode": "synthetic" if self.synthetic else "real_device", "status": "connecting"}
            self.path = self.root / "runs" / self.run["id"]
            atomic_json(self.path / "run.json", self.run)
            self.thread = threading.Thread(target=self._worker, name="automatic-blink-source", daemon=False)
            self.thread.start()
        return self.status()

    def _append(self, name, value):
        payload = (json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n").encode()
        if self.byte_count + len(payload) > MAX_RAW:
            raise ValueError("local_run_storage_limit_model_preserved")
        path = self.path / name
        if path.is_symlink():
            raise ValueError("symlink_run_file")
        with path.open("ab") as stream:
            stream.write(payload)
        self.byte_count += len(payload)

    def _load_learning(self):
        total, examples = 0, []
        paths = sorted((self.root / "runs").glob("run-*/examples.jsonl"))
        if len(paths) > 4096:
            raise ValueError("learning_history_capacity_model_preserved")
        for path in paths:
            if path.is_symlink() or path.stat().st_size > MAX_RAW:
                raise ValueError("invalid_learning_history")
            total += path.stat().st_size
            if total > MAX_RAW:
                raise ValueError("learning_history_capacity_model_preserved")
            for line in path.read_text().splitlines():
                example = json.loads(line)
                if example.get("id") != "example-" + _digest({k: v for k, v in example.items() if k != "id"}):
                    raise ValueError("learning_example_integrity_mismatch")
                if example.get("partition") != "learning":
                    raise ValueError("check_data_in_learning_history")
                if example.get("contract") == self.contract:
                    examples.append(example)
        return examples

    def _open(self):
        if self.synthetic:
            source_id = "synthetic"
        else:
            discovery = self.sources.discover()
            found = [s for s in discovery["sources"] if s["id"] != "synthetic"]
            if len(found) != 1:
                raise ValueError("Start one Muse LSL stream, then press Train." if not found
                                 else "More than one EEG source found. Leave only your Muse stream running, then press Train.")
            source_id = found[0]["id"]
        source = self.sources.open(source_id)
        with self.lock:
            self.source = source
            description = copy.deepcopy(source.description)
            self.rate = description["sample_rate_hz"]
            self.indices = description["frontal_indices"]
            if not 32 <= self.rate <= 1024 or len(self.indices) != 2:
                raise ValueError("unsupported_frontal_source")
            self.contract = {"source_mode": self.run["source_mode"], "sample_rate_hz": self.rate,
                             "channels": [[description["channels"][i]["name"].upper(), description["channels"][i]["unit"]]
                                          for i in self.indices]}
            epoch = "automatic-source-" + secrets.token_hex(8)
            self.run.update(source_descriptor=description, source_epoch=epoch, status="learning")
            self.metadata = {"kind": "AcquisitionMetadata", "schema_version": "0.1", "id": "metadata-" + self.run["id"],
                             "session_id": self.run["id"], "device_model": description["name"],
                             "transport": "fixture" if self.synthetic else "lsl", "sample_rate_hz": self.rate,
                             "channels": [{**c, "enabled": True} for c in description["channels"]],
                             "clock_epoch": epoch, "hardware_verified": False, "raw_storage": "local_only",
                             "provenance": {"source_mode": self.run["source_mode"], "creator": FORMAT,
                                            "tool_version": FORMAT, "config_hash": Config().digest,
                                            "input_hashes": [], "seed": 1 if self.synthetic else None}}
            self.learning = self._load_learning()
            self.checkpoint = self.store.latest(self.contract)
            self.detector = PersonalDetector(self.metadata, self.checkpoint, exploratory_metadata=True)
            self.phase, self.message = "learning", "Learning · press B after every deliberate double blink."
            atomic_json(self.path / "run.json", self.run)

    def _worker(self):
        try:
            self._open()
            while not self.cancel.is_set():
                now = self.clock()
                if now - self.started >= 600:
                    self.message = "Ten-minute session finished."
                    break
                if now - self.subscriber_s > 5:
                    self.message = "Page disconnected. Progress saved."
                    break
                rows, times = self.source.pull()
                if times:
                    self.consume(rows, times, self.clock())
                elif self.last_sample_host is not None and now - self.last_sample_host > 2:
                    raise ValueError("EEG stream stopped. Progress saved; reconnect and press Train.")
                elif self.last_sample_host is None and now - self.started > 12:
                    raise ValueError("No EEG samples received. Check your Muse stream and press Train.")
                self._accept_fit()
        except Exception as error:
            with self.lock:
                self.failure = True
                self.message = str(error)
        finally:
            if self.source is not None:
                try:
                    self.source.close()
                except Exception as error:
                    self.failure, self.message = True, "Source close failed: " + str(error)
                self.source = None
            if self.fit_thread is not None:
                self.fit_thread.join(30)
                if self.fit_thread.is_alive():
                    self.failure, self.message = True, "Training worker did not exit."
            self._accept_fit(final=True)
            with self.lock:
                self.stopped = self.clock()
                if self.phase == "checking":
                    try:
                        self._save_check(complete=False)
                    except (ValueError, OSError) as error:
                        self.failure, self.message = True, "Evaluation save failed; checkpoint preserved. " + str(error)
                if self.phase != "complete":
                    self.phase = "error" if self.failure else "stopped"
                if self.checkpoint and not self.failure and self.phase != "complete":
                    self.message = "Model saved—you can use it or continue training."
                elif not self.checkpoint and not self.failure:
                    self.message = "Progress saved. More B labels and background EEG are needed for the first model."
                try:
                    self.run.update(status=self.phase, stopped_ns=time.time_ns(), message=self.message,
                                    checkpoint_id=self.checkpoint["id"] if self.checkpoint else None,
                                    sample_count=self.sample_index, labels=len(self.labels))
                    atomic_json(self.path / "run.json", self.run)
                except OSError as error:
                    self.phase, self.message = "error", "Run summary could not be saved: " + str(error)

    def stop(self):
        with self.lock:
            if self.phase in ACTIVE:
                self.message = "Saving progress…"
            self.cancel.set()
        return self.status()

    def close(self):
        self.closed = True
        self.stop()
        if self.thread:
            self.thread.join(35)
            if self.thread.is_alive():
                raise RuntimeError("automatic_training_source_did_not_exit")
        if self.fit_thread and self.fit_thread.is_alive():
            raise RuntimeError("automatic_training_fitter_did_not_exit")

    def label(self, body):
        if (set(body) != {"id", "client_ms", "run_id"} or not isinstance(body["id"], str)
                or not 1 <= len(body["id"]) <= 80 or not isinstance(body["client_ms"], (int, float))
                or isinstance(body["client_ms"], bool) or not math.isfinite(body["client_ms"])):
            raise ValueError("invalid_B_label")
        with self.lock:
            if not self.run or body["run_id"] != self.run["id"]:
                raise ValueError("stale_training_run_label")
            existing = next((b for b in self.labels if b["id"] == body["id"]), None)
            if existing:
                return {"saved": True, "label_id": existing["id"], "status": self.status()}
            if self.phase not in {"learning", "fitting", "checking"} or self.last_source_s is None:
                raise ValueError("Wait for live EEG before labelling.")
            if len(self.labels) >= 1000:
                raise ValueError("label_capacity_progress_preserved")
            value = {**body, "source_s": self.last_source_s, "host_s": self.clock(),
                     "source_anchor_age_s": self.clock() - self.last_sample_host,
                     "epoch": self.run["source_epoch"], "stage": self.stage,
                     "partition": "checking" if self.phase == "checking" else "learning",
                     "semantics": "reported_double_not_verified_physiological_timing"}
            self._append("labels.jsonl", value)
            self.labels.append(value)
            if value["partition"] == "learning" and value["source_anchor_age_s"] <= .5:
                self._example(value["source_s"], 1, value["id"])
            return {"saved": True, "label_id": value["id"], "status": self.status()}

    def _example(self, end, label, label_id=None):
        start = end - 2
        if start < self.stage_start or any(e["run_id"] == self.run["id"] and max(start, e["start_s"]) < min(end, e["end_s"])
                                           for e in self.learning):
            return
        data = [(t, row) for t, row in self.rows if start - 1 / self.rate <= t <= end]
        try:
            features, times, samples = _features([t for t, _ in data],
                                               [[r[i] for i in self.indices] for _, r in data], self.rate, end_s=end)
        except ValueError:
            return
        value = {"partition": "learning", "run_id": self.run["id"], "stage": self.stage,
                 "created_ns": time.time_ns(), "contract": self.contract, "label": label,
                 "label_id": label_id, "start_s": start, "end_s": end, "features": features,
                 "raw_sha256": _digest([times, samples]), "label_semantics": "B_report" if label else "assumed_background"}
        value["id"] = "example-" + _digest(value)
        self._append("examples.jsonl", value)
        self.learning.append(value)
        self.stage_new[label] += 1

    def consume(self, rows, times, host_s):
        with self.lock:
            if (not 1 <= len(times) == len(rows) <= 128
                    or any(not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0 for t in times)
                    or any(b <= a for a, b in zip(times, times[1:]))
                    or any(len(r) != len(self.metadata["channels"]) or any(not isinstance(v, (int, float))
                           or not math.isfinite(v) or abs(v) > 1e9 for v in r) for r in rows)):
                raise ValueError("invalid_EEG_batch")
            if self.last_source_s is not None and times[0] <= self.last_source_s:
                raise ValueError("Source clock reset. Progress saved; start a fresh run.")
            previous = self.last_source_s
            gap = previous is not None and times[0] - previous > 1.5 / self.rate
            continuous = not gap and all(.5 / self.rate <= b - a <= 1.5 / self.rate for a, b in zip(times, times[1:]))
            if previous is None:
                self.stage_start = times[0]
            self.last_source_s, self.last_sample_host = times[-1], host_s
            if not continuous:
                self.rows.clear()
            self.rows.extend(zip(times, rows))
            raw = {"source_times_s": times, "host_receipt_s": host_s, "samples": rows,
                   "source_epoch": self.run["source_epoch"], "continuous": continuous,
                   "partition": "checking" if self.phase == "checking" else "learning", "stage": self.stage}
            self._append("raw.jsonl", raw)
            # Usability means numerical continuity and nonflat frontal samples,
            # not independently measured electrode contact or hardware identity.
            recent = [r for t, r in self.rows if t >= times[-1] - 1]
            varying = len(recent) >= self.rate * .9 and all(max(r[i] for r in recent) - min(r[i] for r in recent) > 1e-6
                                                          for i in self.indices)
            usable = continuous and varying
            if self.phase == "checking" and usable:
                left = max(self.check_started_source, previous if previous is not None else times[0])
                if self.usable_intervals and abs(self.usable_intervals[-1][1] - left) < 1 / self.rate:
                    self.usable_intervals[-1][1] = times[-1]
                else:
                    self.usable_intervals.append([left, times[-1]])
            # Canonical sample validation is retained, while the acquisition
            # descriptor remains explicitly unverified in the exploratory store.
            from services.bridge.server import chunk
            canonical = chunk(self.metadata, rows, times, self.sequence, self.sample_index, host_s, "auto-host",
                              quality="good" if usable else "bad",
                              gap=max(1, round((times[0] - previous) * self.rate) - 1) if gap else 0)
            self.sequence += 1
            self.sample_index += len(rows)
            try:
                _, gestures = self.detector.consume(canonical)
            except ValueError:
                self.detector.reset("signal_gap")
                self.detector.previous = None
                gestures = []
            if usable and not self.detector.armed and self.detector.count >= self.rate * self.detector.config.warmup_s:
                self.detector.arm()
            if self.phase == "checking":
                for gesture in gestures:
                    if gesture["status"] == "accepted":
                        event = {"id": gesture["id"], "epoch": self.run["source_epoch"],
                                 "final_blink_s": gesture["final_blink"]["seconds"],
                                 "decision_s": gesture["decision"]["seconds"]}
                        self._append("decisions.jsonl", {**event, "checkpoint_id": self.checkpoint["id"], "stage": self.stage})
                        self.check_decisions.append(event)
                self._maybe_check()
            elif self.phase in {"learning", "fitting"}:
                end = times[-1] - 2.25  # Wait for a later B tap before committing a background window.
                if end - self.last_negative_end >= 2 and end - 2 >= self.stage_start:
                    self.last_negative_end = end
                    if not any(max(end - 2, b["source_s"] - 2) <= min(end, b["source_s"] + 2) for b in self.labels):
                        self._example(end, 0)
                if self.phase == "learning":
                    self._maybe_fit()

    def _maybe_fit(self):
        counts = [sum(e["label"] == label for e in self.learning) for label in (0, 1)]
        if min(counts) < 20 or (self.checkpoint is not None and min(self.stage_new) < 10):
            return
        batch = copy.deepcopy(training_batch(self.learning, self.checkpoint))
        parent = copy.deepcopy(self.checkpoint)
        self.phase, self.message = "fitting", "Updating your model · keep labelling with B."
        self.fit_result = self.fit_error = None

        def fit():
            try:
                result = fit_checkpoint(batch, copy.deepcopy(self.contract), parent)
                self.store.save(result)  # Save valid weights before any evaluation.
                with self.lock:
                    self.fit_result = result
            except Exception as error:
                with self.lock:
                    self.fit_error = str(error)
        self.fit_thread = threading.Thread(target=fit, name="automatic-blink-fit", daemon=False)
        self.fit_thread.start()

    def _accept_fit(self, final=False):
        with self.lock:
            if self.fit_error is not None:
                self.failure, self.message = True, "Training update failed; saved checkpoints remain usable. " + self.fit_error
                self.fit_error = None
                self.cancel.set()
            if self.fit_result is None:
                return
            self.checkpoint, self.fit_result = self.fit_result, None
            self.evaluation = None
            if final or self.cancel.is_set():
                return
            self.stage += 1
            self.stage_start = self.last_source_s
            self.stage_label_start = len(self.labels)
            self.check_started_host, self.check_started_source = self.clock(), self.last_source_s
            self.stage_new, self.check_decisions, self.usable_intervals = [0, 0], [], []
            self.detector = PersonalDetector(self.metadata, self.checkpoint, exploratory_metadata=True)
            self.phase, self.message = "checking", "Model saved · checking against fresh B labels."
            self._append("stages.jsonl", {"stage": self.stage, "partition": "checking", "source_s": self.stage_start,
                                         "checkpoint_id": self.checkpoint["id"]})

    def _save_check(self, complete):
        labels = self.labels[self.stage_label_start:]
        end = self.last_source_s or self.check_started_source
        usable_s = sum(right - left for left, right in self.usable_intervals)
        exclusions = [(b["source_s"] - 2, b["source_s"] + 2) for b in labels]
        excluded = sum(union_seconds(exclusions, left, right) for left, right in self.usable_intervals)
        report = check_metrics(labels, self.check_decisions, elapsed_s=max(0, self.clock() - self.check_started_host),
                               usable_s=usable_s, background_s=max(0, usable_s - excluded), complete=complete)
        report.update(run_id=self.run["id"], stage=self.stage, source_end_s=end,
                      source_mode=self.run["source_mode"], refit_evidence="within_run_only")
        self.evaluation = report
        self.store.save_evaluation(self.checkpoint["id"], report)
        return report

    def _maybe_check(self):
        # Reports shown in the UI do not end a round early. Leave the newest
        # detections time to receive their after-blink B label before matching.
        elapsed = self.clock() - self.check_started_host
        labels = self.labels[self.stage_label_start:]
        if len(labels) < 30 or elapsed < 120:
            return
        last = max([b["source_s"] for b in labels] + [d["final_blink_s"] for d in self.check_decisions], default=0)
        if self.last_source_s - last < 1.25:
            return
        report = self._save_check(complete=True)
        if not report["complete"]:
            return
        self._append("checks.jsonl", report)
        if report["target_reached"]:
            self.phase, self.message = "complete", "Target reached against your B labels. Model saved and ready to use."
            self.cancel.set()
        else:
            self.stage += 1
            self.stage_start, self.stage_new = self.last_source_s, [0, 0]
            self.phase, self.message = "learning", "Model saved · collecting more examples to improve it."
            self._append("stages.jsonl", {"stage": self.stage, "partition": "learning", "source_s": self.stage_start})
