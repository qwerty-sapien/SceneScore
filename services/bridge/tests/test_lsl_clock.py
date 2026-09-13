"""Clock arithmetic fixtures; no measured headset/LSL performance."""
from types import SimpleNamespace
import pytest
from services.bridge.lsl_clock import LSLClock


def test_native_correction_midpoint_and_uncertainty_are_preserved():
    def correction(obj, remote, uncertainty, timeout, error):
        remote._obj.value = 98
        uncertainty._obj.value = .004
        return .1
    ticks = iter([200, 200.002])
    clock = LSLClock(SimpleNamespace(obj=None), SimpleNamespace(local_clock=lambda: 100),
                     native=correction, monotonic=lambda: next(ticks))
    probe = clock.probe()
    assert probe['offset_s'] == pytest.approx(100.101)
    assert probe['device_s'] == pytest.approx(99.901)
    assert probe['uncertainty_s'] == pytest.approx(.005)
    assert probe['native_remote_s'] == 98


def test_clock_errors_and_observed_drift_are_not_hidden():
    def failure(obj, remote, uncertainty, timeout, error):
        error._obj.value = -1
        return 0
    clock = LSLClock(SimpleNamespace(obj=None), SimpleNamespace(local_clock=lambda: 100), native=failure)
    with pytest.raises(ValueError, match='correction_unavailable'):
        clock.probe()
    offsets = iter([.1, .13])
    def correction(obj, remote, uncertainty, timeout, error):
        uncertainty._obj.value = .003
        return next(offsets)
    ticks = iter([200, 200, 202, 202])
    locals_ = iter([100, 102])
    clock = LSLClock(SimpleNamespace(obj=None), SimpleNamespace(local_clock=lambda: next(locals_)),
                     native=correction, monotonic=lambda: next(ticks))
    assert clock.probe()['uncertainty_s'] == pytest.approx(.003)
    assert clock.probe()['uncertainty_s'] == pytest.approx(.033)
