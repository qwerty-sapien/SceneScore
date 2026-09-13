import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import math

spec = importlib.util.spec_from_file_location('muse_blinks', Path(__file__).parents[1] / 'muse_blinks.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BlinkTests(unittest.TestCase):
    def test_signal_double(self):
        detector = module.Detector(calibration=3)
        events = [e for t, row in module.synthetic(7, 3) for e in detector.feed(t, row)]
        self.assertEqual(sum(e['event'] == 'double_blink' for e in events), 1)

    def test_noise_only(self):
        detector = module.Detector(calibration=3)
        events = [e for t, row in module.synthetic(8, 100) for e in detector.feed(t, row)]
        self.assertFalse(any(e['event'] == 'double_blink' for e in events))

    def test_triple_and_single_rejected(self):
        for count in (1, 3):
            detector = module.Detector()
            detector.pending = [{'peak_s': i * .4, 'end_s': i * .4 + .1} for i in range(count)]
            self.assertEqual(detector.close(2)[0]['event'], 'rejected_train')

    def test_no_prefix_commit(self):
        detector = module.Detector()
        detector.pending = [{'peak_s': 1, 'end_s': 1.1}, {'peak_s': 1.4, 'end_s': 1.5}]
        self.assertEqual(detector.close(1.9), [])
        detector.pending.append({'peak_s': 1.8, 'end_s': 1.9})
        self.assertEqual(detector.close(2.5)[0]['event'], 'rejected_train')

    def test_gap_and_nonfinite_stop(self):
        for t, row in ((1, [2, 3]), (.01, [float('nan'), 3])):
            detector = module.Detector()
            detector.feed(0, [2, 3])
            with self.assertRaises(ValueError):
                detector.feed(t, row)

    def test_cooldown(self):
        detector = module.Detector()
        detector.cooldown = 3
        detector.pending = [{'peak_s': 1, 'end_s': 1.1}, {'peak_s': 1.4, 'end_s': 1.5}]
        self.assertEqual(detector.close(2.1)[0]['event'], 'rejected_train')

    def test_triple_waveform_never_emits_double(self):
        detector = module.Detector(calibration=3)
        events = []
        for i in range(8 * 256):
            t = i / 256
            x = 2 * math.sin(2 * math.pi * 3 * t)
            x += sum(160 * math.exp(-((t - peak) / .045) ** 2) for peak in (4, 4.4, 4.8))
            events.extend(detector.feed(t, [800 + x, 810 + .95 * x]))
        self.assertEqual(sum(e['event'] == 'blink' for e in events), 3)
        self.assertFalse(any(e['event'] == 'double_blink' for e in events))

    def test_flat_calibration_rejected(self):
        detector = module.Detector(calibration=3)
        with self.assertRaisesRegex(ValueError, 'Flat EEG'):
            for i in range(3 * 256):
                detector.feed(i / 256, [800, 810])

    def test_live_read_error_releases_board(self):
        board = MagicMock()
        board.get_board_data.side_effect = RuntimeError('test disconnect')
        shim = MagicMock(return_value=board)
        shim.get_sampling_rate.return_value = 256
        shim.get_eeg_names.return_value = ['TP9', 'AF7', 'AF8', 'TP10']
        shim.get_eeg_channels.return_value = [1, 2, 3, 4]
        fake = SimpleNamespace(BoardShim=shim, BrainFlowInputParams=MagicMock(),
                               BoardIds=SimpleNamespace(MUSE_2016_BOARD=SimpleNamespace(value=41)))
        args = SimpleNamespace(name=None, calibration=3, threshold=5, gap=.5, seconds=7)
        with patch.dict('sys.modules', {'brainflow': MagicMock(), 'brainflow.board_shim': fake}):
            with self.assertRaisesRegex(RuntimeError, 'test disconnect'):
                module.live(args)
        board.stop_stream.assert_called_once()
        board.release_session.assert_called_once()


if __name__ == '__main__':
    unittest.main()
