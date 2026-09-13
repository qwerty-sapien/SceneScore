"""LSL source-to-host calibration with measured native uncertainty, no EEG edits."""
from __future__ import annotations
import ctypes
import math
import time


class LSLClock:
    """Bridge the LSL native clocks to Python monotonic by a measured midpoint.

    lsl_time_correction_ex is the documented liblsl C API. Its uncertainty is a
    measured network round-trip quantity; retain all of it, not a precision claim.
    The detector timestamps stay in the original stream clock.
    """
    def __init__(self, inlet, pylsl_module, *, native=None, monotonic=time.monotonic):
        if native is None:
            from pylsl.lib import lib
            native = lib.lsl_time_correction_ex
            native.restype = ctypes.c_double
            native.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double),
                               ctypes.POINTER(ctypes.c_double), ctypes.c_double, ctypes.POINTER(ctypes.c_int)]
        self.inlet, self.pylsl, self.native, self.monotonic = inlet, pylsl_module, native, monotonic
        self.previous = None

    def probe(self):
        remote, uncertainty, error = ctypes.c_double(), ctypes.c_double(), ctypes.c_int()
        correction = self.native(self.inlet.obj, ctypes.byref(remote), ctypes.byref(uncertainty),
                                 ctypes.c_double(.2), ctypes.byref(error))
        if error.value:
            raise ValueError('lsl_clock_correction_unavailable')
        before = self.monotonic()
        local = self.pylsl.local_clock()
        after = self.monotonic()
        values = (remote.value, uncertainty.value, correction, before, local, after)
        if not all(math.isfinite(value) for value in values) or uncertainty.value < 0 or after < before:
            raise ValueError('invalid_lsl_clock_correction')
        offset = correction + (before + after) / 2 - local
        source_now = after - offset
        # The observed change in correction explicitly contributes to uncertainty;
        # reject excessive clock movement instead of silently assuming unit rate.
        drift = 0.0 if self.previous is None else abs(offset - self.previous[1])
        if self.previous and after <= self.previous[0]:
            raise ValueError('nonmonotonic_lsl_clock_probe')
        self.previous = (after, offset)
        return {'device_s': source_now, 'host_s': after,
                'uncertainty_s': uncertainty.value + (after - before) / 2 + drift,
                'native_remote_s': remote.value, 'offset_s': offset,
                'method': 'lsl_time_correction_ex_plus_host_midpoint'}
