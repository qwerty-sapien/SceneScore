"""Connection faults stay distinct; diagnostics never starts a raw source."""

import copy
import time

from services.training.diagnostics import Diagnostics, checklist, signal_metrics
from services.training.state import Workspace
from services.training.tests.test_training import http_workspace, manual, wait


def state(connected=False, mode=None, reason="No source selected"):
    return {"connected": connected, "mode": mode, "reason": reason, "sample_rate_hz": 256}


def stages(status, metrics=None, discovery=None, bluetooth=None, age=0):
    return {
        s["id"]: s
        for s in checklist(
            status,
            metrics or {"age_s": None, "channels": [], "window_s": 0, "gaps": 0, "rate_hz": None},
            discovery or {"sources": [], "observed": [], "blockers": []},
            bluetooth or {"power": "on", "authorization": "allowed", "devices": []},
            age,
        )
    }


def test_connected_bluetooth_does_not_claim_outlet_or_samples():
    result = stages(
        state(),
        bluetooth={
            "power": "on",
            "authorization": "allowed",
            "devices": [{"name": "Muse fixture", "system_connected": True}],
        },
    )
    assert result["bluetooth"]["state"] == result["device"]["state"] == "pass"
    assert result["stream"]["state"] == result["samples"]["state"] == "blocked"
    assert "pairing alone" in result["stream"]["action"]


def test_advertising_and_permission_are_not_connection_evidence():
    result = stages(
        state(),
        bluetooth={
            "power": "on",
            "authorization": "allowed",
            "devices": [{"name": "Muse fixture", "system_connected": False}],
        },
    )
    assert result["device"]["state"] == "warning"
    assert "not established" in result["device"]["detail"]
    result = stages(state(), bluetooth={"authorization": "denied"})
    assert result["bluetooth"]["state"] == "blocked"
    assert "Privacy & Security" in result["bluetooth"]["action"]


def test_bad_descriptor_is_reported_separately_from_absent_stream():
    result = stages(
        state(),
        discovery={
            "sources": [],
            "observed": [{"name": "Muse", "error": "two_identified_frontal_microvolt_channels_required"}],
        },
    )
    assert result["stream"]["state"] == "blocked"
    assert "metadata is incompatible" in result["stream"]["detail"]
    assert "units" in result["stream"]["action"]


def test_signal_metrics_keep_raw_values_and_expose_flatline_gap_rate_and_age(tmp_path):
    workspace = manual(tmp_path)
    try:
        rows = [(i / 256, [0, i % 7], False) for i in range(513)]
        untouched = copy.deepcopy(rows)
        metrics = signal_metrics(rows, workspace.metadata, workspace.source, 10, 10.1)
        assert rows == untouched
        assert metrics["channels"][0]["flat"] and not metrics["channels"][1]["flat"]
        assert metrics["rate_hz"] == 256
        result = stages(state(True, "real_device"), metrics)
        assert result["samples"]["state"] == "pass"
        assert result["signal"]["state"] == "warning"
        rows[300] = (*rows[300][:2], True)
        metrics = signal_metrics(rows, workspace.metadata, workspace.source, 10, 11)
        assert metrics["gaps"] == 1 and metrics["rate_hz"] is None
        assert stages(state(True, "real_device"), metrics)["samples"]["state"] == "blocked"
        metrics.update(age_s=0.1, gaps=0, rate_hz=200, channels=[])
        assert "differs" in stages(state(True, "real_device"), metrics)["signal"]["detail"]
    finally:
        workspace.close()


def test_hardware_observations_expire_and_synthetic_cannot_certify_device():
    result = stages(state(True, "synthetic"), age=21)
    assert result["bluetooth"]["state"] == result["stream"]["state"] == "unknown"
    assert "no hardware claim" in result["inlet"]["detail"]


def test_monitor_automatically_finds_sources_but_never_opens_one_and_closes(tmp_path):
    class Sources:
        def __init__(self):
            self.calls = 0

        def discover(self):
            self.calls += 1
            return {"sources": [{"id": "fixture"}], "observed": [], "blockers": []}

        def open(self, _):
            raise AssertionError("diagnostics must not connect or collect EEG")

    sources = Sources()
    workspace = Workspace(tmp_path, sources=sources)
    monitor = workspace.diagnostics = Diagnostics(
        workspace, interval=0.05, bluetooth_probe=lambda *_: {"authorization": "allowed", "power": "on", "devices": []}
    )
    try:
        assert sources.calls == 0
        monitor.monitor({"enabled": True})
        wait(lambda: monitor.snapshot()["checked_at"] is not None)
        assert monitor.snapshot()["discovery"]["sources"][0]["id"] == "fixture"
        assert workspace.worker is None and workspace.recorder is None
        with monitor.lock:
            monitor.last_poll = time.monotonic() - 6
        monitor.wake.set()
        wait(lambda: not monitor.enabled)
        monitor.monitor({"enabled": True})
        wait(lambda: sources.calls >= 2)
    finally:
        worker = monitor.worker
        workspace.close()
        assert worker is None or not worker.is_alive()
        assert monitor.active_process is None


def test_authenticated_diagnostic_routes_and_permission_request_are_explicit(tmp_path):
    with http_workspace(tmp_path) as (workspace, _, request):
        calls = []
        workspace.sources.discover = lambda: {"sources": [], "observed": [], "blockers": []}
        workspace.diagnostics.bluetooth_probe = lambda permission, connected: (
            calls.append(permission) or {"authorization": "not_requested", "devices": []}
        )
        assert request("GET", "/v1/diagnostics", token="wrong")[0] == 403
        assert request("GET", "/v1/diagnostics")[1]["enabled"] is False
        assert request("POST", "/v1/diagnostics/monitor", {"enabled": True})[0] == 200
        wait(lambda: len(calls) >= 1)
        assert calls[0] is False
        assert request("POST", "/v1/diagnostics/check", {"request_bluetooth_permission": True})[0] == 200
        wait(lambda: True in calls)
        report = request("GET", "/v1/diagnostics")[1]
        assert report["configuration"]["env_placeholders_used"] is False
        assert "samples" not in report["signal"]
        assert request("POST", "/v1/diagnostics/monitor", {"enabled": False})[0] == 200
