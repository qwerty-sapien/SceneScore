"""Bounded causal mapping of Muse logical sample time to host receipt time.

Classic EEG counters identify sample order, not capture latency. A constant
one-way BLE delay is unidentifiable from these observations. The default 25ms
allowance is an explicit uncalibrated uncertainty floor, NOT a measured physical
upper bound. It deliberately exceeds the unchanged browser 20ms timing gate.
No clean synthetic receipt fixture can certify real capture-clock accuracy.
"""
from __future__ import annotations

from collections import deque
import math
from statistics import median


class ClockError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BLEClock:
    """Robust recent slope/offset fit, with bounded history and no future samples.

    Observe a completed frame's LAST logical sample time against its EARLIEST
    channel notification receipt. This avoids adding four-channel assembly delay
    and the eleven earlier samples' packetization interval to the clock anchor.
    The fit is to receipt time, retaining the unresolved BLE delay explicitly.
    A Theil-Sen slope from pairs >=1 second apart resists isolated receipt bursts;
    a median intercept resists outliers. The maximum residual still contributes
    to uncertainty, so robustness never silently removes observed timing jitter.
    Assembled frames are ordered by source index; their earliest receipts need
    not be ordered. Backward receipt anchors are omitted from fitting, while
    their discrepancy remains a bounded uncertainty contribution. The transport
    separately validates monotonic notification callback timestamps.
    """

    UNCALIBRATED_DELAY_ALLOWANCE_S = .025
    MAX_RATE_DEVIATION = .005
    METHOD = "bounded_theil_sen_receipt_fit_uncalibrated_ble_delay"

    def __init__(self, *, max_history: int = 128, history_seconds: float = 8.0):
        if (type(max_history) is not int or not 8 <= max_history <= 256
                or not math.isfinite(history_seconds) or not 2 <= history_seconds <= 30):
            raise ValueError("invalid_ble_clock_bounds")
        self.max_history = max_history
        self.history_seconds = history_seconds
        self.reset()

    def reset(self) -> None:
        self._history: deque[tuple[float, float]] = deque(maxlen=self.max_history)
        self._reorders: deque[tuple[float, float]] = deque(maxlen=self.max_history)
        self._last_source_s: float | None = None
        self._reordered_receipt_count = 0
        self._rate = 1.0
        self._offset = 0.0
        self._jitter_s = 0.0
        self._rate_uncertainty = self.MAX_RATE_DEVIATION
        self._rate_clipped = False
        self._last_probe_s: float | None = None

    def observe(self, device_s: float, receipt_s: float) -> None:
        if (not math.isfinite(device_s) or not math.isfinite(receipt_s)
                or device_s < 0 or receipt_s < 0):
            raise ClockError("invalid_ble_clock_observation")
        if self._last_source_s is not None and device_s <= self._last_source_s:
            raise ClockError("packet_clock_reset")
        self._last_source_s = device_s
        if self._history and receipt_s < self._history[-1][1]:
            # Different channels can deliver N+1 before the first channel of N.
            # Keep the unchanged receipt value out of the fit, rather than
            # rewriting it or mistaking source-ordered delivery for clock reset.
            discrepancy = abs(receipt_s - (self._offset + device_s * self._rate))
            self._reorders.append((self._history[-1][1],
                                   max(discrepancy, self._history[-1][1] - receipt_s)))
            self._reordered_receipt_count += 1
            return
        self._history.append((device_s, receipt_s))
        while len(self._history) > 1 and receipt_s - self._history[0][1] > self.history_seconds:
            self._history.popleft()
        points = tuple(self._history)
        slopes = [(end[1] - start[1]) / (end[0] - start[0])
                  for i, start in enumerate(points) for end in points[i + 1:]
                  if end[0] - start[0] >= 1.0]
        raw_rate = median(slopes) if slopes else 1.0
        self._rate = min(1 + self.MAX_RATE_DEVIATION,
                         max(1 - self.MAX_RATE_DEVIATION, raw_rate))
        self._rate_clipped = self._rate != raw_rate
        # Center computations near the current source time for numeric stability
        # after many packet-counter rollovers.
        pivot = device_s
        center = median(host - (source - pivot) * self._rate for source, host in points)
        self._offset = center - pivot * self._rate
        self._jitter_s = max(abs(host - (center + (source - pivot) * self._rate))
                             for source, host in points)
        span = points[-1][0] - points[0][0]
        # A stable receipt series does not prove oscillator stability. Retain
        # 100ppm extrapolation allowance; short fits retain the full rate budget.
        self._rate_uncertainty = (max(.0001, 2 * self._jitter_s / span,
                                      abs(raw_rate - self._rate))
                                  if slopes and span > 0 else self.MAX_RATE_DEVIATION)

    def _age(self, now_s: float) -> float:
        if not self._history:
            raise ClockError("source_clock_unavailable")
        if (not math.isfinite(now_s) or now_s < self._history[-1][1]
                or (self._last_probe_s is not None and now_s < self._last_probe_s)):
            raise ClockError("invalid_ble_clock_probe")
        return now_s - self._history[-1][1]

    def probe(self, now_s: float) -> dict[str, float | str | bool]:
        age = self._age(now_s)
        self._last_probe_s = now_s
        # Extrapolate the logical clock to the probe's CURRENT host timestamp.
        # Returning the last packet as if it were current would bias browser RTT
        # anchors by packet age, even though the original pair remained valid.
        uncertainty = (self.UNCALIBRATED_DELAY_ALLOWANCE_S + self._jitter_s
                       + self._reorder_uncertainty(now_s)
                       + self._rate_uncertainty * age + age)
        return {"device_s": (now_s - self._offset) / self._rate,
                "host_s": now_s, "uncertainty_s": uncertainty,
                "method": self.METHOD, "transport_delay_verified": False}

    def _reorder_uncertainty(self, now_s: float) -> float:
        while self._reorders and now_s - self._reorders[0][0] > self.history_seconds:
            self._reorders.popleft()
        return max((uncertainty for _, uncertainty in self._reorders), default=0.0)

    def diagnostics(self, now_s: float) -> dict[str, float | int | str | bool]:
        age = self._age(now_s)
        return {"method": self.METHOD, "observation_count": len(self._history),
                "history_span_s": self._history[-1][0] - self._history[0][0],
                "rate": self._rate, "rate_clipped": self._rate_clipped,
                "offset_s": self._offset, "jitter_s": self._jitter_s,
                "reordered_receipt_count": self._reordered_receipt_count,
                "reorder_uncertainty_s": self._reorder_uncertainty(now_s),
                "rate_uncertainty": self._rate_uncertainty,
                "last_observation_age_s": age,
                "uncalibrated_delay_allowance_s": self.UNCALIBRATED_DELAY_ALLOWANCE_S,
                "transport_delay_verified": False}
