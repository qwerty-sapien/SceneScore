"""Local MU-02 double-blink prototype. No recording or music control side effects."""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
import statistics
import sys
import time


class Detector:
    """Causal bilateral excursion detector; experimental, not an intent classifier."""

    def __init__(self, rate=256, calibration=10, threshold=5, gap=.5):
        self.rate, self.calibration, self.threshold, self.gap = rate, calibration, threshold, gap
        self.history = [deque(maxlen=round(rate * calibration)) for _ in range(2)]
        self.base = self.smooth = self.scale = None
        self.count = 0
        self.active = None
        self.pending = []
        self.ambiguous = False
        self.cooldown = -math.inf
        self.last_t = None
        self.last_end = -math.inf

    def feed(self, t, values):
        if not math.isfinite(t) or len(values) != 2 or not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid EEG sample; restart and recalibrate')
        if self.last_t is not None and not 0 < t - self.last_t < .1:
            raise ValueError('EEG timestamp gap/reset; restart and recalibrate')
        self.last_t = t
        if self.base is None:
            self.base, self.smooth = list(values), [0., 0.]
        for i, x in enumerate(values):
            self.base[i] += (1 - math.exp(-2 * math.pi * .5 / self.rate)) * (x - self.base[i])
            self.smooth[i] += (1 - math.exp(-2 * math.pi * 10 / self.rate)) * (x - self.base[i] - self.smooth[i])
        self.count += 1
        if self.scale is None:
            for history, value in zip(self.history, self.smooth):
                history.append(value)
            if self.count >= round(self.calibration * self.rate):
                scales = []
                for history in self.history:
                    values = list(history)[self.rate:]  # discard initial filter settling
                    center = statistics.median(values)
                    scales.append(max(7., 1.4826 * statistics.median(abs(v - center) for v in values)))
                    if max(values) - min(values) < .1:
                        raise ValueError('Flat EEG channel during calibration; check fit and restart')
                self.scale = scales
                return [{'event': 'ready', 'noise_scale_uv': scales}]
            return []
        scores = [abs(v) / s for v, s in zip(self.smooth, self.scale)]
        events = []
        score = min(scores)
        if self.active is None and score >= self.threshold and t - self.last_end >= .15:
            # Close an earlier train before starting a separated one.
            events.extend(self.close(t))
            self.active = [t, t, score, t < self.cooldown]
        if self.active is not None:
            if score > self.active[2]:
                self.active[1:3] = [t, score]
            # Suppress gross excursions and waveforms with implausible duration.
            self.active[3] |= max(scores) > 60 or t - self.active[0] > .45
            if max(scores) <= self.threshold * .4:
                start, peak, strength, invalid = self.active
                if .04 <= t - start <= .45 and not invalid:
                    if self.pending and peak - self.pending[-1]['peak_s'] < .2:
                        self.ambiguous = True
                    self.pending.append({'peak_s': peak, 'end_s': t})
                    if len(self.pending) > 3:
                        self.pending = self.pending[-3:]
                        self.ambiguous = True
                    events.append({'event': 'blink', 'peak_s': peak, 'score': strength})
                else:
                    self.ambiguous = True
                self.active = None
                self.last_end = t
        if self.active is None:
            events.extend(self.close(t))
        return events

    def close(self, t):
        if not self.pending:
            self.ambiguous = False
            return []
        if t - self.pending[-1]['end_s'] <= self.gap:
            return []
        count = len(self.pending)
        accepted = count == 2 and not self.ambiguous and t >= self.cooldown
        result = {'event': 'double_blink' if accepted else 'rejected_train',
                  'blink_count': count, 'decision_s': t,
                  'final_blink_s': self.pending[-1]['end_s']}
        if accepted:
            self.cooldown = t + 1.
        self.pending.clear()
        self.ambiguous = False
        return [result]


def synthetic(seconds, calibration):
    """Deterministic signal fixture; never presented as headset evidence."""
    for i in range(round(seconds * 256)):
        t = i / 256
        x = 2 * math.sin(2 * math.pi * 3 * t) + math.sin(2 * math.pi * 7 * t)
        for peak in (calibration + 1, calibration + 1.4):
            x += 160 * math.exp(-((t - peak) / .045) ** 2)
        yield t, [800 + x, 810 + x * .95]


def live(args, *, on_event=None, on_sample=None, stop=None):
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

    params = BrainFlowInputParams()
    params.timeout = 15
    if args.name:
        params.serial_number = args.name
    board_id = BoardIds.MUSE_2016_BOARD.value
    board = BoardShim(board_id, params)
    prepared = started = False
    try:
        print('Connecting to MU-02 via Bluetooth. Headset must be unplugged.', file=sys.stderr)
        board.prepare_session()
        prepared = True
        rate = BoardShim.get_sampling_rate(board_id)
        names = BoardShim.get_eeg_names(board_id)
        eeg_rows = BoardShim.get_eeg_channels(board_id)
        rows = [eeg_rows[names.index(name)] for name in ('AF7', 'AF8')]
        timestamp_row = BoardShim.get_timestamp_channel(board_id)
        print(f'BrainFlow metadata: {rate} Hz, AF7/AF8, uV. Contact quality is unverified.', file=sys.stderr)
        detector = Detector(rate, args.calibration, args.threshold, args.gap)
        board.start_stream()
        started = True
        begin = last_data = time.monotonic()
        print(f'Calibrating for {args.calibration:g}s. Sit relaxed; then try double blinks after READY.', file=sys.stderr)
        while time.monotonic() - begin < args.seconds:
            if stop is not None and stop.is_set():
                break
            data = board.get_board_data()
            if data.shape[1]:
                last_data = time.monotonic()
                for column in range(data.shape[1]):
                    timestamp = float(data[timestamp_row, column])
                    values = [float(data[row, column]) for row in rows]
                    for event in detector.feed(timestamp, values):
                        (on_event or emit)(event, 'real_device')
                    if on_sample is not None:
                        on_sample(timestamp, detector.smooth, detector.count, rate, args.calibration)
            elif time.monotonic() - last_data > 3:
                raise RuntimeError('No EEG for 3 seconds. Check charge, fit and other connected apps; restart.')
            time.sleep(.02)
    finally:
        try:
            if started:
                board.stop_stream()
        finally:
            if prepared:
                board.release_session()


def emit(event, mode):
    print(json.dumps({'prototype_version': 1, 'source_mode': mode, **event}), flush=True)
    if event['event'] == 'ready':
        print('READY — try a deliberate double blink. Ctrl-C stops.', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true', help='Run a labelled synthetic fixture, without Bluetooth')
    parser.add_argument('--name', help='Optional Bluetooth name such as Muse-1234')
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--calibration', type=float, default=10)
    parser.add_argument('--threshold', type=float, default=5, help='Noise multiplier; lower is more sensitive')
    parser.add_argument('--gap', type=float, default=.5, help='Sequence closure time after blink end, in seconds')
    args = parser.parse_args()
    if not (3 <= args.calibration <= 30 and args.calibration + 3 <= args.seconds <= 3600
            and 2 <= args.threshold <= 20 and .2 <= args.gap <= .8):
        parser.error('Use calibration 3..30, seconds calibration+3..3600, threshold 2..20, gap .2...8')
    try:
        if args.simulate:
            detector = Detector(calibration=args.calibration, threshold=args.threshold, gap=args.gap)
            for t, values in synthetic(args.seconds, args.calibration):
                for event in detector.feed(t, values):
                    emit(event, 'synthetic')
        else:
            live(args)
    except KeyboardInterrupt:
        print('Stopped.', file=sys.stderr)
    except (ImportError, ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
