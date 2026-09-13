"""Local-only classic Muse frame adapter into the existing Companion pipeline."""
from __future__ import annotations

import copy
import hashlib
import json
import secrets
import time

from modules.muse.baseline.causal import CausalBaseline
from modules.muse.runtime.quality import QualityGate
from scenescore.contracts import validate

VERSION = 'scenescore-muse-ble-1'
TRANSPORT_CONFIG = {
    'version': VERSION, 'transport': 'bleak', 'profile': 'classic-muse-gatt',
    'preset': 'p21', 'sample_rate_hz': 256, 'samples_per_packet': 12,
    'required_packet_channels': ['TP9', 'AF7', 'AF8', 'TP10'],
    'enabled_channels': ['AF7', 'AF8'], 'unit': 'uV',
    'conversion': '(unsigned12-2048)*125/256',
    'chunk_sample_origin': 'first_observed_frame_boundary',
}
CONFIG_HASH = hashlib.sha256(json.dumps(TRANSPORT_CONFIG, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def ble_metadata(*, hardware_verified=False):
    """Fresh session/clock identities with a deterministic acquisition binding.

    Contract 0.1 requires real_device metadata to be hardware-verified. Before
    first verified samples this is an inert synthetic-provenance placeholder,
    never a source of samples or an HTTP metadata/clock response. The adapter
    changes the provenance to real_device only after a full valid EEG frame.
    hardware_verified=True also validates an optional profile's eventual binding.
    """
    session = 'ble-' + secrets.token_hex(12)
    metadata = {
        'kind': 'AcquisitionMetadata', 'schema_version': '0.1', 'id': session + '-metadata',
        'provenance': {'source_mode': 'real_device' if hardware_verified else 'synthetic',
                       'creator': VERSION, 'tool_version': VERSION,
                       'config_hash': CONFIG_HASH, 'input_hashes': [], 'seed': None},
        'session_id': session, 'device_model': 'Muse classic GATT', 'transport': 'bleak',
        'sample_rate_hz': 256,
        'channels': [{'name': name, 'unit': 'uV', 'enabled': True} for name in ('AF7', 'AF8')],
        'clock_epoch': 'ble-device-' + secrets.token_hex(12),
        'hardware_verified': hardware_verified, 'raw_storage': 'local_only',
    }
    validate(metadata)
    return metadata


class BleCompanionSource:
    """Callbacks for BleMuseManager; no server import and no recording surface."""

    def __init__(self, companion, quality_profile=None):
        self.companion = companion
        self.quality_profile = copy.deepcopy(quality_profile)
        # Reject a wrong/synthetic profile before acquisition is permitted. The
        # temporary binding is not installed as connected or verified metadata.
        QualityGate(ble_metadata(hardware_verified=True), quality_profile)
        self.manager = None
        self._sequence = 0
        self._first_frame = True
        self._sample_origin = 0

    def attach(self, manager):
        self.manager = manager
        with self.companion.lock:
            self.companion.source_clock_required = True
            self.companion.source_clock_probe = None

    def begin(self, _device_name):
        companion = self.companion
        with companion.lock:
            companion.metadata = ble_metadata()
            companion.detector = CausalBaseline(companion.metadata)
            companion.host_epoch = 'ble-host-' + secrets.token_hex(12)
            companion.mode = 'LIVE_MUSE'
            companion.connected = False
            companion.available = True
            companion.stream_verified = False
            companion.quality_gate = None
            companion.quality = 'unverified'
            companion.reason = 'waiting_for_verified_ble_samples'
            companion.sample_count = 0
            companion.last_device_s = 0.
            companion.last_host_s = time.monotonic()
            companion.source_clock_required = True
            companion.source_clock_probe = None
            # Preserve cursor monotonicity while discarding events from old epochs.
            companion.events.clear()
            companion._emit('status', at_s=0., reason=companion.reason)
            self._sequence, self._first_frame = 0, True

    def consume_frame(self, frame):
        companion = self.companion
        with companion.lock:
            if self._first_frame:
                verified = copy.deepcopy(companion.metadata)
                verified['hardware_verified'] = True
                verified['provenance']['source_mode'] = 'real_device'
                validate(verified)
                quality_gate = QualityGate(verified, self.quality_profile)
                companion.metadata = verified
                companion.detector = CausalBaseline(verified)
                companion.quality_gate = quality_gate
                companion.stream_verified = True
                companion.source_clock_probe = self.manager.clock_probe if self.manager else None
                # Canonical chunks start at local index zero plus observed drops;
                # a headset's arbitrary initial counter is not prior data loss.
                # Device timestamps retain the unwrapped source counter clock.
                self._sample_origin = frame.first_sample_index - frame.dropped_samples
                self._first_frame = False
            metadata = companion.metadata
            # All four channels were required for protocol assembly; only the two
            # frontal channels conduct and participate in this quality binding.
            raw = {
                'kind': 'EEGChunk', 'schema_version': '0.1',
                'id': metadata['session_id'] + f'-{self._sequence}',
                'provenance': metadata['provenance'], 'session_id': metadata['session_id'],
                'sequence': self._sequence, 'sample_start_index': frame.first_sample_index - self._sample_origin,
                'sample_rate_hz': 256, 'channels': metadata['channels'],
                'device_times_s': list(frame.device_times_s), 'device_epoch': metadata['clock_epoch'],
                'host_receipt': {'seconds': frame.received_monotonic_s,
                                 'clock': 'host_monotonic', 'epoch': companion.host_epoch},
                'samples': [[row[1], row[2]] for row in frame.samples_uv],
                'dropped_samples_before': frame.dropped_samples,
                'quality': {'state': 'unverified', 'reason': 'contact_quality_unverified'}, 'imu': None,
            }
            if frame.dropped_samples:
                companion.detector.reset('sample_gap_rearm_required')
            raw['quality'] = companion.quality_gate.consume(raw)
            companion.consume(raw)
            self._sequence += 1

    def fault(self, reason):
        companion = self.companion
        with companion.lock:
            companion.fault(reason)
            companion.stream_verified = False
            companion.source_clock_probe = None
            # Invalidate browser anchors immediately, even before explicit reconnect.
            # Preserve valid historical real-device metadata. stream_verified
            # is false, so status cannot imply current hardware verification.
            companion.metadata = copy.deepcopy(companion.metadata)
            companion.metadata['clock_epoch'] = 'ble-invalid-' + secrets.token_hex(12)
            companion.host_epoch = 'ble-host-invalid-' + secrets.token_hex(12)
            companion.events.clear()
            companion._emit('status', at_s=companion.last_device_s, reason=reason)

    def discontinuity(self, reason):
        """Disarm on an invalid packet while preserving the current source epoch."""
        companion = self.companion
        with companion.lock:
            companion.detector.reset(reason)
            if companion.quality_gate is not None:
                companion.quality_gate.reset()
            companion.quality = 'unverified'
            companion.reason = reason
            companion._emit('status', at_s=companion.last_device_s, reason=reason)
