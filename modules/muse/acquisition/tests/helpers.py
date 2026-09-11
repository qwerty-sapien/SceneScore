import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]


def metadata():
    return copy.deepcopy(json.loads((ROOT / 'fixtures/contracts/AcquisitionMetadata.json').read_text()))


def chunk(sequence=0, start=0, count=64, value=0.0, epoch='fixture-1', gap=0, quality='good'):
    meta = metadata()
    return {'kind': 'EEGChunk', 'schema_version': '0.1', 'id': f'chunk-{sequence}',
            'provenance': meta['provenance'], 'session_id': meta['session_id'],
            'sequence': sequence, 'sample_start_index': start, 'sample_rate_hz': 256,
            'channels': meta['channels'], 'device_times_s': [(start+i)/256 for i in range(count)],
            'device_epoch': epoch, 'host_receipt': {'seconds': 10+start/256, 'clock': 'host_monotonic', 'epoch': 'host-1'},
            'samples': [[value, value] for _ in range(count)], 'dropped_samples_before': gap,
            'quality': {'state': quality, 'reason': None if quality == 'good' else 'test_fault'}, 'imu': None}
