"""Deterministic clock simulations, never physical BLE latency evidence."""
import math

import pytest

from modules.muse.acquisition.ble_clock import BLEClock, ClockError


def test_no_clock_before_samples_and_reset_removes_anchor():
    clock = BLEClock()
    with pytest.raises(ClockError, match="^source_clock_unavailable$"):
        clock.probe(100)
    clock.observe(0, 100)
    clock.reset()
    with pytest.raises(ClockError, match="^source_clock_unavailable$"):
        clock.probe(101)


def test_exact_synthetic_arrivals_still_retain_unknown_delay_floor():
    clock = BLEClock()
    for index in range(128):
        device = (index * 12 + 11) / 256
        clock.observe(device, 100 + device)
    now = 100 + device
    probe = clock.probe(now)
    assert probe["device_s"] == pytest.approx(device)
    assert probe["host_s"] == now
    assert probe["uncertainty_s"] >= .025
    assert probe["uncertainty_s"] > .02  # existing browser gate is unchanged
    assert probe["transport_delay_verified"] is False
    assert clock.diagnostics(now)["jitter_s"] < 1e-12


def test_constant_unidentifiable_transport_delay_cannot_be_declared_measured():
    clocks = [BLEClock(), BLEClock()]
    for source in range(10):
        clocks[0].observe(source, 100 + source)
        clocks[1].observe(source, 100 + source + .2)
    # Offset absorbs this delay. Identical residuals cannot reveal its magnitude.
    assert clocks[0].diagnostics(109)["jitter_s"] < 1e-12
    assert clocks[1].diagnostics(109.2)["jitter_s"] < 1e-12
    assert clocks[1].probe(109.2)["transport_delay_verified"] is False


def test_drift_is_causally_estimated_and_probe_refers_to_current_host_time():
    clock = BLEClock()
    for index in range(128):
        source = 5000 + index / 20
        clock.observe(source, 100 + source * 1.001)
    now = 100 + source * 1.001 + .01
    probe = clock.probe(now)
    assert probe["device_s"] == pytest.approx((now - 100) / 1.001)
    assert clock.diagnostics(now)["rate"] == pytest.approx(1.001, abs=1e-10)
    assert probe["uncertainty_s"] >= .035


def test_receipt_outlier_does_not_move_fit_but_remains_uncertainty():
    clock = BLEClock()
    for index in range(100):
        source = index / 10
        clock.observe(source, 100 + source + (.04 if index == 70 else 0))
    diagnostic = clock.diagnostics(109.9)
    assert diagnostic["rate"] == pytest.approx(1, abs=1e-10)
    assert diagnostic["jitter_s"] >= .039999
    assert clock.probe(109.9)["uncertainty_s"] >= .064999


def test_stale_stream_increases_uncertainty_instead_of_freezing_good_anchor():
    clock = BLEClock()
    for index in range(20):
        clock.observe(index / 10, 100 + index / 10)
    initial = clock.probe(101.9)
    stale = clock.probe(102.4)
    assert stale["uncertainty_s"] > initial["uncertainty_s"] + .5
    assert stale["device_s"] == pytest.approx(2.4)


def test_history_bounded_by_count_and_time():
    clock = BLEClock(max_history=16, history_seconds=2)
    for index in range(100):
        clock.observe(index / 100, 100 + index / 100)
    assert clock.diagnostics(100.99)["observation_count"] == 16
    clock.observe(10, 110)
    assert clock.diagnostics(110)["observation_count"] == 1


def test_probe_cannot_rewrite_an_earlier_result_with_future_samples():
    clock = BLEClock()
    for index in range(30):
        clock.observe(index / 10, 100 + index / 10)
    earlier = clock.probe(102.9)
    unchanged = dict(earlier)
    clock.observe(3, 103.04)
    assert earlier == unchanged
    assert clock.probe(103.04)["uncertainty_s"] > earlier["uncertainty_s"]
    with pytest.raises(ClockError, match="^invalid_ble_clock_probe$"):
        clock.probe(102.9)


@pytest.mark.parametrize("source,receipt", [(-1, 0), (0, -1), (math.nan, 0), (0, math.inf)])
def test_invalid_observations(source, receipt):
    with pytest.raises(ClockError, match="^invalid_ble_clock_observation$"):
        BLEClock().observe(source, receipt)


@pytest.mark.parametrize("source,receipt", [(1, 102), (0, 102)])
def test_source_counter_reset_requires_epoch(source, receipt):
    clock = BLEClock()
    clock.observe(1, 101)
    with pytest.raises(ClockError, match="^packet_clock_reset$"):
        clock.observe(source, receipt)


def test_backward_receipt_anchor_is_skipped_without_reset_or_timestamp_rewrite():
    clock = BLEClock(history_seconds=2)
    clock.observe(1, 101)
    initial = clock.probe(101)
    clock.observe(1.05, 100.98)
    after = clock.probe(101)
    assert after["device_s"] == initial["device_s"]
    assert after["host_s"] == initial["host_s"]
    assert after["uncertainty_s"] >= initial["uncertainty_s"] + .069999
    info = clock.diagnostics(101)
    assert info["observation_count"] == 1
    assert info["reordered_receipt_count"] == 1
    assert info["reorder_uncertainty_s"] >= .069999
    # Even an omitted source anchor advances source continuity tracking.
    with pytest.raises(ClockError, match="^packet_clock_reset$"):
        clock.observe(1.05, 101.05)
    clock.observe(1.1, 101.1)
    assert clock.diagnostics(101.1)["observation_count"] == 2
    # The discrepancy is retained only for the bounded recent history window.
    clock.observe(4, 104)
    assert clock.diagnostics(104)["reorder_uncertainty_s"] == 0


def test_reset_clears_omitted_receipt_anchors_and_source_continuity():
    clock = BLEClock()
    clock.observe(1, 101)
    clock.observe(1.05, 100.98)
    clock.reset()
    clock.observe(0, 200)
    assert clock.diagnostics(200)["reordered_receipt_count"] == 0
    assert clock.diagnostics(200)["reorder_uncertainty_s"] == 0


def test_implausible_drift_clipped_and_residual_not_hidden():
    clock = BLEClock()
    for index in range(30):
        clock.observe(index / 10, 100 + index / 10 * 1.02)
    info = clock.diagnostics(100 + 2.9 * 1.02)
    assert info["rate_clipped"] is True
    assert info["rate"] == 1.005
    assert info["jitter_s"] > .02
