"""Live evidence for connection debugging. No EEG capture or automatic source selection."""

from collections import deque
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import threading
import time


def utc():
    return datetime.now(timezone.utc).isoformat()


def signal_metrics(rows, metadata, source, last_host_s, now):
    age = None if last_host_s is None else max(0, now - last_host_s)
    if not rows or not metadata or not source:
        return {"age_s": age, "window_s": 0, "channels": [], "gaps": 0, "rate_hz": None}
    recent = [r for r in rows if r[0] >= rows[-1][0] - 2]
    span = recent[-1][0] - recent[0][0]
    gaps = sum(bool(r[2]) for r in recent[1:])
    channels = []
    for index in source["frontal_indices"]:
        values = [r[1][index] for r in recent]
        low, high = min(values), max(values)
        channels.append(
            {
                "name": metadata["channels"][index]["name"],
                "unit": metadata["channels"][index]["unit"],
                "min": low,
                "max": high,
                "peak_to_peak": high - low,
                "flat": len(values) >= 32 and high == low,
            }
        )
    return {
        "age_s": age,
        "window_s": span,
        "channels": channels,
        "gaps": gaps,
        "rate_hz": (len(recent) - 1) / span if span >= 0.5 and not gaps else None,
    }


def checklist(status, metrics, discovery, bluetooth, checked_age):
    """Evidence tiers deliberately do not equate advertising, LSL and physiological EEG."""
    stages = []

    def add(key, label, state, detail, action=""):
        stages.append({"id": key, "label": label, "state": state, "detail": detail, "action": action})

    add("service", "Local service", "pass", "Authenticated loopback service is responding.")
    stale = checked_age is None or checked_age > 20
    auth, power = bluetooth.get("authorization"), bluetooth.get("power")
    if stale:
        add(
            "bluetooth",
            "Bluetooth adapter",
            "unknown",
            "Hardware check pending or stale.",
            "Enable automatic checks or check now.",
        )
    elif auth in {"denied", "restricted", "not_requested"}:
        add(
            "bluetooth",
            "Bluetooth adapter",
            "blocked",
            "Bluetooth permission: " + auth,
            "Allow Bluetooth for the app running the launcher (usually Terminal) in macOS Privacy & Security. Use Enable Bluetooth check if not requested.",
        )
    elif power == "on":
        add("bluetooth", "Bluetooth adapter", "pass", "macOS reports Bluetooth powered on.")
    elif power == "off":
        add(
            "bluetooth",
            "Bluetooth adapter",
            "blocked",
            "macOS reports Bluetooth powered off.",
            "Turn on Bluetooth in macOS.",
        )
    else:
        add(
            "bluetooth",
            "Bluetooth adapter",
            "unknown",
            bluetooth.get("error") or "Bluetooth state: " + str(power or "unavailable"),
            "Restart Launch Blink Trainer.command to build the local Bluetooth helper.",
        )
    devices = bluetooth.get("devices", [])
    linked = [d for d in devices if d.get("system_connected")]
    if not stale and linked:
        add(
            "device",
            "Muse Bluetooth service",
            "pass",
            "macOS reports a connected Muse-service peripheral: " + ", ".join(d["name"] for d in linked),
        )
    elif not stale and devices:
        add(
            "device",
            "Muse Bluetooth service",
            "warning",
            "Muse-service advertisement seen; connection not established by this check.",
            "Start the Muse-to-LSL app for this headset. Check whether another app or phone is holding it.",
        )
    else:
        add(
            "device",
            "Muse Bluetooth service",
            "unknown",
            "No current Muse-service observation; this does not prove the headset is disconnected.",
            "Power on the headset and check distance, Bluetooth permission, and the streaming app.",
        )
    sources, observed = discovery.get("sources", []), discovery.get("observed", [])
    if stale:
        add("stream", "LSL EEG stream", "unknown", "Discovery pending or stale.")
    elif sources:
        add("stream", "LSL EEG stream", "pass", f"{len(sources)} compatible advertised stream(s); descriptor checked.")
    elif observed:
        add(
            "stream",
            "LSL EEG stream",
            "blocked",
            "EEG outlet found, but its metadata is incompatible: "
            + "; ".join(o.get("error", "") for o in observed if o.get("error")),
            "Check frontal channel names/order, µV units, nominal rate and unique source ID in the streaming app.",
        )
    else:
        add(
            "stream",
            "LSL EEG stream",
            "blocked",
            "; ".join(discovery.get("blockers", [])) or "No EEG outlet advertised.",
            "Start the Muse-to-LSL stream on this Mac. Bluetooth pairing alone does not create an LSL stream.",
        )
    connected, synthetic = status["connected"], status["mode"] == "synthetic"
    add(
        "inlet",
        "Selected source",
        "pass" if connected else "warning",
        ("Synthetic rehearsal inlet connected; no hardware claim." if synthetic else "Selected LSL inlet connected.")
        if connected
        else (status.get("reason") or "No source selected."),
        ""
        if connected
        else "Select the discovered EEG source and connect it. No automatic reconnection or recording occurs.",
    )
    age = metrics["age_s"]
    fresh = connected and age is not None and age <= 0.5
    if fresh:
        add(
            "samples",
            "Incoming samples",
            "pass",
            f"{'Synthetic' if synthetic else 'Raw numeric'} samples arriving; last batch {age * 1000:.0f} ms ago.",
        )
    elif connected and age is None:
        add(
            "samples",
            "Incoming samples",
            "warning",
            "Inlet connected; waiting for its first samples.",
            "Confirm streaming is started in the Muse app, not only connected.",
        )
    else:
        add(
            "samples",
            "Incoming samples",
            "blocked",
            "No fresh samples. " + (status.get("reason") or ""),
            "Inspect the streaming app's packet counter, headset power and Bluetooth connection; reconnect the selected source after a fault.",
        )
    flat = [c["name"] for c in metrics["channels"] if c["flat"]]
    nominal, rate = status.get("sample_rate_hz"), metrics["rate_hz"]
    mismatch = rate is not None and nominal and abs(rate / nominal - 1) > 0.02
    if not fresh or metrics["window_s"] < 0.5:
        add("signal", "Signal continuity", "unknown", "Need fresh samples and at least half a second of coverage.")
    elif flat or metrics["gaps"] or mismatch:
        detail = []
        if flat:
            detail.append("Constant samples: " + ", ".join(flat))
        if metrics["gaps"]:
            detail.append(f"{metrics['gaps']} timestamp gap(s) in the last two seconds")
        if mismatch:
            detail.append(f"Observed {rate:.1f} Hz differs from declared {nominal:g} Hz")
        add(
            "signal",
            "Signal continuity",
            "warning",
            "; ".join(detail),
            "Inspect raw traces and sensor contact; check the stream's rate/units. This is not a contact-quality diagnosis.",
        )
    else:
        add(
            "signal",
            "Signal continuity",
            "pass",
            "Varying samples, continuous timestamps and consistent declared rate. Electrode contact remains unverified.",
        )
    return stages


class Diagnostics:
    def __init__(self, workspace, *, bluetooth_probe=None, interval=10):
        self.workspace = workspace
        self.bluetooth_probe = bluetooth_probe or self._bluetooth
        self.interval = interval
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.worker = None
        self.enabled = False
        self.request_permission = False
        self.last_poll = time.monotonic()
        self.checked_at = None
        self.checked_monotonic = None
        self.checking = False
        self.discovery = {"sources": [], "observed": [], "blockers": []}
        self.bluetooth = {}
        self.events = deque(maxlen=20)
        self.last_states = {}
        self.active_process = None

    def monitor(self, body):
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("diagnostics_enabled_boolean_required")
        with self.lock:
            if self.workspace.closed:
                raise ValueError("workspace_closed")
            self.enabled = enabled
            self.last_poll = time.monotonic()
            if enabled and (self.worker is None or not self.worker.is_alive()):
                self.stop.clear()
                self.worker = threading.Thread(target=self._run, name="muse-diagnostics", daemon=False)
                self.worker.start()
            self.wake.set()
        return self.snapshot()

    def check_now(self, body):
        if not isinstance(body.get("request_bluetooth_permission", False), bool):
            raise ValueError("permission_flag_boolean_required")
        with self.lock:
            self.request_permission |= body.get("request_bluetooth_permission") is True
        return self.monitor({"enabled": True})

    def _bluetooth(self, permission, connected):
        helper = Path(__file__).resolve().parents[2] / "artifacts/muse-bluetooth-probe"
        if not helper.is_file():
            return {"error": "Bluetooth helper unavailable; start the local launcher.", "devices": []}
        command = [str(helper)]
        if permission:
            command.append("--request-permission")
        if connected:
            command.append("--no-scan")
        with self.lock:
            if self.stop.is_set():
                return {"error": "stopped", "devices": []}
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.active_process = process  # exact task-owned identity, reaped below
        try:
            output, _ = process.communicate(timeout=7)
            if process.returncode != 0 or len(output) > 16384:
                return {"error": "Bluetooth probe failed; check macOS Bluetooth permission.", "devices": []}
            return json.loads(output)
        except (subprocess.TimeoutExpired, ValueError):
            process.kill()
            process.communicate()
            return {"error": "Bluetooth probe timed out or returned invalid metadata.", "devices": []}
        finally:
            with self.lock:
                self.active_process = None

    def _run(self):
        try:
            while not self.stop.is_set():
                self.wake.clear()
                with self.lock:
                    if not self.enabled or time.monotonic() - self.last_poll > 5:
                        self.enabled = False
                        break
                    self.checking = True
                    permission, self.request_permission = self.request_permission, False
                try:
                    discovered = self.workspace.sources.discover()
                    bluetooth = self.bluetooth_probe(permission, self.workspace.status()["connected"])
                    with self.lock:
                        self.discovery, self.bluetooth = discovered, bluetooth
                        self.checked_at, self.checked_monotonic = utc(), time.monotonic()
                except Exception as exc:
                    with self.lock:
                        self.discovery = {"sources": [], "observed": [], "blockers": [str(exc)[:300]]}
                        self.bluetooth = {"error": "Hardware check incomplete", "devices": []}
                        self.checked_at, self.checked_monotonic = utc(), time.monotonic()
                finally:
                    with self.lock:
                        self.checking = False
                # Check the subscriber each second; wake immediately for explicit recheck.
                deadline = time.monotonic() + self.interval
                while not self.stop.is_set() and time.monotonic() < deadline:
                    if self.wake.wait(min(1, max(0, deadline - time.monotonic()))):
                        break
                    with self.lock:
                        if not self.enabled or time.monotonic() - self.last_poll > 5:
                            break
        finally:
            with self.lock:
                self.checking = False
                self.worker = None
                if self.enabled and not self.stop.is_set() and time.monotonic() - self.last_poll <= 5:
                    self.worker = threading.Thread(target=self._run, name="muse-diagnostics", daemon=False)
                    self.worker.start()

    def snapshot(self):
        now = time.monotonic()
        with self.workspace.lock:
            status = self.workspace.status()
            metrics = signal_metrics(
                list(self.workspace.rows),
                self.workspace.metadata,
                self.workspace.source,
                self.workspace.last_host_s,
                now,
            )
        with self.lock:
            self.last_poll = now
            age = None if self.checked_monotonic is None else max(0, now - self.checked_monotonic)
            stages = checklist(status, metrics, self.discovery, self.bluetooth, age)
            for stage in stages:
                if self.last_states.get(stage["id"]) != stage["state"]:
                    self.events.appendleft(
                        {"at": utc(), "stage": stage["label"], "state": stage["state"], "detail": stage["detail"]}
                    )
                    self.last_states[stage["id"]] = stage["state"]
            return {
                "version": "muse-diagnostics-1",
                "enabled": self.enabled,
                "checking": self.checking,
                "checked_at": self.checked_at,
                "check_age_s": age,
                "stages": stages,
                "signal": metrics,
                "discovery": copy.deepcopy(self.discovery),
                "bluetooth": copy.deepcopy(self.bluetooth),
                "events": list(self.events),
                "source_mode": status["mode"],
                "configuration": {
                    "transport": "lsl",
                    "board_id": "not used by LSL",
                    "units": "from source descriptor; frontal µV required",
                    "env_placeholders_used": False,
                },
            }

    def close(self):
        with self.lock:
            self.enabled = False
            self.stop.set()
            self.wake.set()
            process, worker = self.active_process, self.worker
            if process is not None and process.poll() is None:
                process.terminate()
        if worker is not None:
            worker.join(timeout=12)
            if worker.is_alive():
                raise RuntimeError("diagnostics_shutdown_incomplete")
