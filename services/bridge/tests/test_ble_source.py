"""Direct BLE-to-Companion software fixtures; never hardware/participant evidence."""
from copy import deepcopy
import json
import math
import time

import pytest

from modules.muse.acquisition.muse_protocol import EEGFrame
from modules.muse.acquisition.tests.test_ble_manager import (
    connect, manager_factory, on_loop, wait_for,
)
from modules.muse.runtime.quality import calibrate_profile, digest
from modules.muse.runtime.tests.test_quality import profile as synthetic_profile, training_session
from services.bridge.ble_source import BleCompanionSource, ble_metadata
from services.bridge.server import Companion
from scenescore.contracts import validate


class InspectableCompanion(Companion):
    def __init__(self):
        super().__init__(ble_metadata(), mode='LIVE_MUSE')
        self.fixture_chunks = []

    def consume(self, raw):
        self.fixture_chunks.append(deepcopy(raw))
        return super().consume(raw)


def fixture_frame(index, receipt=None, *, dropped=0, amplitude=10):
    rows = tuple((999., amplitude * math.sin(2 * math.pi * 8 * (index * 12 + i) / 256),
                  amplitude * math.cos(2 * math.pi * 8 * (index * 12 + i) / 256), -999.)
                 for i in range(12))
    at = time.monotonic() if receipt is None else receipt
    return EEGFrame(index & 65535, index, rows, at, at, dropped)


def fixture_real_profile():
    # Deliberately constructed in-memory branch-coverage fixture. These strings
    # are not real consent, independent review, calibration, or hardware evidence.
    meta = ble_metadata(hardware_verified=True)
    session = training_session(meta)
    session['labels'] = [{'source': 'independent_observation', 'reviewer': 'software-fixture-not-a-human'}]
    session['consent_ref'] = 'software-fixture-not-participant-consent'
    session['content_sha256'] = digest({k: session[k] for k in ('metadata', 'chunks', 'labels')})
    return calibrate_profile(meta, [session])


def test_metadata_has_fresh_identity_and_stable_transport_binding():
    one, two = ble_metadata(), ble_metadata()
    assert one['session_id'] != two['session_id'] and one['clock_epoch'] != two['clock_epoch']
    assert one['provenance']['config_hash'] == two['provenance']['config_hash']
    assert one['provenance']['source_mode'] == 'synthetic'  # inert pending metadata only
    assert ble_metadata(hardware_verified=True)['provenance']['source_mode'] == 'real_device'
    assert one['transport'] == 'bleak' and one['raw_storage'] == 'local_only'
    assert one['sample_rate_hz'] == 256 and not one['hardware_verified']
    assert one['channels'] == [{'name': name, 'unit': 'uV', 'enabled': True} for name in ('AF7', 'AF8')]


def test_complete_frames_become_canonical_frontal_chunks_but_missing_profile_cannot_arm(manager_factory):
    companion = InspectableCompanion()
    source = BleCompanionSource(companion)
    manager, _, _ = manager_factory(on_begin=source.begin, on_frame=source.consume_frame,
                                    on_fault=source.fault, on_discontinuity=source.discontinuity)
    source.attach(manager)
    assert not companion.status()['hardware_verified']
    assert companion.sample_count == 0 and companion.fixture_chunks == []
    connect(manager)
    status = companion.status()
    assert status['connected'] and status['hardware_verified']
    assert status['quality'] == 'unverified' and not status['armed']
    assert status['reason'] == 'calibrated_quality_profile_missing'
    raw = companion.fixture_chunks[0]
    validate(raw)
    assert all(c['provenance']['source_mode'] == 'real_device' for c in companion.fixture_chunks)
    assert raw['sample_rate_hz'] == 256 and len(raw['samples']) == 12
    assert len(raw['samples'][0]) == 2 and raw['sample_start_index'] == 0
    assert raw['host_receipt']['epoch'] == status['host_epoch']
    assert raw['device_epoch'] == status['device_epoch']
    assert companion.clock()['uncertainty_s'] >= .025
    assert 'samples' not in json.dumps(status) and 'samples_uv' not in json.dumps(manager.snapshot())
    with pytest.raises(ValueError, match='quality_not_verified_good'):
        companion.arm()


def test_both_frontal_columns_and_timestamps_are_preserved_without_ear_quality_prerequisite():
    companion = InspectableCompanion()
    source = BleCompanionSource(companion)
    source.begin('Muse-fixture')
    frame = fixture_frame(50)
    source.consume_frame(frame)
    raw = companion.fixture_chunks[-1]
    assert raw['samples'] == [[row[1], row[2]] for row in frame.samples_uv]
    assert raw['device_times_s'] == list(frame.device_times_s)
    assert raw['host_receipt']['seconds'] == frame.received_monotonic_s
    assert [c['name'] for c in companion.quality_gate.metadata['channels']] == ['AF7', 'AF8']


def test_invalid_or_synthetic_quality_profile_is_rejected_before_connection():
    with pytest.raises(ValueError, match='quality_profile_binding_or_hash_mismatch'):
        BleCompanionSource(InspectableCompanion(), synthetic_profile())
    with pytest.raises(ValueError, match='invalid_quality_profile_fields'):
        BleCompanionSource(InspectableCompanion(), {'good': True})


def test_real_profile_gate_warmup_arm_and_bad_signal_share_existing_causal_pipeline():
    companion = InspectableCompanion()
    source = BleCompanionSource(companion, fixture_real_profile())
    source.begin('Muse-fixture')
    start = time.monotonic() - 3
    for index in range(64):
        source.consume_frame(fixture_frame(index, start + index * 12 / 256))
    status = companion.status()
    assert status['quality'] == 'good' and status['warmup_ready'] and not status['armed']
    assert companion.arm()['armed']
    source.consume_frame(fixture_frame(64, time.monotonic(), amplitude=1000))
    status = companion.status()
    assert status['quality'] == 'bad' and not status['armed']
    assert status['reason'] == 'signal_amplitude_outside_calibration'


def test_gap_accounting_disarms_and_never_fills_missing_samples():
    companion = InspectableCompanion()
    source = BleCompanionSource(companion, fixture_real_profile())
    source.begin('Muse-fixture')
    source.consume_frame(fixture_frame(100))
    companion.detector.armed = True  # force a prior state only to verify invalidation
    source.consume_frame(fixture_frame(102, dropped=12))
    raw = companion.fixture_chunks[-1]
    assert raw['sample_start_index'] == 24 and raw['dropped_samples_before'] == 12
    assert len(raw['samples']) == 12
    assert not companion.status()['armed']
    assert companion.status()['quality'] == 'bad'


def test_malformed_packet_immediately_disarms_without_faking_a_reconnect(manager_factory):
    companion = InspectableCompanion()
    source = BleCompanionSource(companion)
    manager, _, factory = manager_factory(on_begin=source.begin, on_frame=source.consume_frame,
                                           on_fault=source.fault, on_discontinuity=source.discontinuity)
    source.attach(manager)
    connect(manager)
    epoch = companion.metadata['clock_epoch']
    companion.detector.armed = True
    from modules.muse.acquisition.muse_protocol import EEG_CHARACTERISTICS
    on_loop(manager, lambda: factory.clients[0].callbacks[EEG_CHARACTERISTICS['AF7']](None, b'bad'))
    assert not companion.detector.armed and not companion.detector.grammar.pending
    assert companion.metadata['clock_epoch'] == epoch
    assert manager.snapshot()['bluetooth_state'] == 'streaming'
    assert not manager.snapshot()['reconnect_required']


def test_disconnect_invalidates_epochs_pending_events_and_stream_verification(manager_factory):
    companion = InspectableCompanion()
    source = BleCompanionSource(companion)
    manager, _, factory = manager_factory(on_begin=source.begin, on_frame=source.consume_frame,
                                           on_fault=source.fault)
    source.attach(manager)
    connect(manager)
    before, cursor = companion.status(), companion.cursor
    old_session = companion.metadata['session_id']
    companion.detector.armed = True
    companion.detector.grammar.pending.append({'fixture': True})
    manager.disconnect()
    failed = companion.status()
    assert not failed['connected'] and not failed['armed'] and not failed['hardware_verified']
    assert failed['device_epoch'] != before['device_epoch'] and failed['host_epoch'] != before['host_epoch']
    assert not companion.detector.grammar.pending and companion.cursor > cursor
    with pytest.raises(ValueError, match='source_clock_unavailable'):
        companion.clock()
    connect(manager)
    after = companion.status()
    assert after['device_epoch'] != before['device_epoch'] and after['host_epoch'] != before['host_epoch']
    assert companion.metadata['session_id'] != old_session
    assert after['connected'] and not after['armed'] and after['sample_count'] == 12
    assert len(factory.clients) == 2


def test_unexpected_disconnect_callback_faults_actual_companion(manager_factory):
    companion = InspectableCompanion()
    source = BleCompanionSource(companion)
    manager, _, factory = manager_factory(on_begin=source.begin, on_frame=source.consume_frame,
                                           on_fault=source.fault)
    source.attach(manager)
    connect(manager)
    companion.detector.armed = True
    def drop():
        client = factory.clients[0]
        client.is_connected = False
        client.disconnected_callback(client)
    on_loop(manager, drop)
    wait_for(lambda: not companion.connected)
    assert not companion.detector.armed and not companion.stream_verified
    assert companion.reason == 'unexpected_disconnect_reconnect_required'
