"""Deterministic fake-Bleak lifecycle tests; no Bluetooth hardware or real EEG."""
import asyncio
from concurrent.futures import CancelledError
import json
import threading
import time
from types import SimpleNamespace

import pytest

from modules.muse.acquisition.ble import BleMuseError, BleMuseManager, safe_error_code
from modules.muse.acquisition.muse_protocol import (
    ATHENA_UUID, CONTROL_UUID, EEG_CHARACTERISTICS, SERVICE_UUID, encode_command,
)


def packet(index=100, value=2048):
    pair = bytes((value >> 4, ((value & 15) << 4) | (value >> 8), value & 255))
    return index.to_bytes(2, 'big') + pair * 6


class FakeScanner:
    def __init__(self, names=('Muse-AD3C', 'Headphones', 'Muse-B123', 'Muse-evil\nname')):
        self.devices = [SimpleNamespace(name=name, address=f'opaque-corebluetooth-{i}') for i, name in enumerate(names)]
        self.error = None
        self.wait = False
        self.started = threading.Event()
        self.loop_ids = []

    async def discover(self, *, timeout, return_adv):
        self.loop_ids.append(id(asyncio.get_running_loop()))
        assert timeout <= 120 and return_adv
        self.started.set()
        if self.error:
            raise self.error
        if self.wait:
            await asyncio.sleep(100)
        return {d.address: (d, SimpleNamespace(local_name=d.name)) for d in self.devices}


class FakeClient:
    def __init__(self, device, disconnected_callback, *, athena=False, missing=False,
                 stream=True, drop=None, disconnect_error=False, connect_error=None):
        self.device, self.disconnected_callback = device, disconnected_callback
        chars = [CONTROL_UUID, *EEG_CHARACTERISTICS.values()]
        if athena:
            chars.append(ATHENA_UUID)
        if missing:
            chars.pop()
        self.services = [SimpleNamespace(uuid=SERVICE_UUID, characteristics=[SimpleNamespace(uuid=u) for u in chars])]
        self.is_connected = False
        self.stream, self.drop = stream, drop
        self.disconnect_error, self.connect_error = disconnect_error, connect_error
        self.operations, self.loop_ids, self.callbacks = [], [], {}
        self.disconnect_calls = self.connect_calls = 0

    def mark(self, operation):
        self.operations.append(operation)
        self.loop_ids.append(id(asyncio.get_running_loop()))
        if self.drop == operation:
            self.is_connected = False
            self.disconnected_callback(self)

    async def connect(self):
        self.connect_calls += 1
        if self.connect_error:
            raise self.connect_error
        self.is_connected = True
        self.mark('connect')

    async def start_notify(self, uuid, callback):
        self.callbacks[uuid] = callback
        self.mark('notify:' + uuid)

    async def stop_notify(self, uuid):
        self.mark('stop:' + uuid)
        self.callbacks.pop(uuid, None)

    async def write_gatt_char(self, uuid, data, *, response):
        assert uuid == CONTROL_UUID and response is False
        command = data[1:-1].decode('ascii')
        assert data == encode_command(command)
        self.mark('write:' + command)
        if command == 'd' and self.stream and self.is_connected:
            self.emit(100)

    def emit(self, index):
        for uuid in EEG_CHARACTERISTICS.values():
            self.callbacks[uuid](None, packet(index))

    async def disconnect(self):
        self.disconnect_calls += 1
        self.mark('disconnect')
        if self.disconnect_error:
            raise RuntimeError('native disconnect exception with private address')
        self.is_connected = False
        self.disconnected_callback(self)


class FakeFactory:
    def __init__(self, **options):
        self.options, self.clients = options, []

    def __call__(self, device, *, disconnected_callback):
        client = FakeClient(device, disconnected_callback, **self.options)
        self.clients.append(client)
        return client


@pytest.fixture
def manager_factory():
    managers = []

    def create(*, scanner=None, client=None, **options):
        scanner, client = scanner or FakeScanner(), client or FakeFactory()
        manager = BleMuseManager(scanner_factory=scanner, client_factory=client,
                                 scan_timeout_s=.05, connect_timeout_s=.1,
                                 stream_timeout_s=.1, stage_delay_s=0, **options)
        managers.append(manager)
        return manager, scanner, client

    yield create
    for manager in managers:
        try:
            manager.close()
        except BleMuseError:
            pass
        assert not manager.thread_alive


def connect(manager, session='browser-session'):
    device_id = manager.scan(session)['devices'][0]['id']
    return manager.connect(device_id, session)


def on_loop(manager, function):
    async def invoke():
        return function()
    return asyncio.run_coroutine_threadsafe(invoke(), manager._loop).result(2)


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('fake lifecycle did not finish')


def test_scan_sanitizes_names_and_returns_session_scoped_opaque_handles(manager_factory):
    manager, scanner, _ = manager_factory()
    results = manager.scan('session')['devices']
    assert [row['name'] for row in results] == ['Muse-AD3C', 'Muse-B123']
    assert all(set(row) == {'id', 'name'} for row in results)
    assert all(row['id'] != scanner.devices[0].address for row in results)
    assert 'opaque-corebluetooth' not in json.dumps(results)


def test_connect_uses_actual_ble_device_and_one_event_loop(manager_factory):
    frames, begun = [], []
    manager, scanner, factory = manager_factory(on_frame=frames.append, on_begin=begun.append)
    result = connect(manager)
    client = factory.clients[0]
    assert client.device is scanner.devices[0]
    assert len(set(scanner.loop_ids + client.loop_ids)) == 1
    assert begun == ['Muse-AD3C']
    assert len(frames) == 1 and len(frames[0].samples_uv) == 12
    assert result['bluetooth_state'] == 'streaming' and result['eeg_sample_count'] == 12
    assert set(client.callbacks) == {CONTROL_UUID, *EEG_CHARACTERISTICS.values()}
    assert client.operations[:10] == [
        'connect', 'notify:' + CONTROL_UUID, 'write:h', 'write:p21',
        *('notify:' + uuid for uuid in EEG_CHARACTERISTICS.values()), 'write:d'][:10]
    assert not {'samples', 'samples_uv', 'device_times_s', 'address'} & result.keys()


@pytest.mark.parametrize(('options', 'code'), [
    ({'athena': True}, 'unsupported_athena_profile'),
    ({'missing': True}, 'gatt_profile_mismatch'),
])
def test_profile_validation_precedes_control_commands(manager_factory, options, code):
    manager, _, factory = manager_factory(client=FakeFactory(**options))
    with pytest.raises(BleMuseError, match=code):
        connect(manager)
    assert not any(op.startswith('write:') for op in factory.clients[0].operations)
    assert manager.snapshot()['disconnect_stage'] == 'gatt_inspection'


def test_classic_characteristics_must_belong_to_muse_service(manager_factory):
    factory = FakeFactory()
    original = factory.__class__.__call__
    class WrongService(FakeFactory):
        def __call__(self, device, **kwargs):
            client = original(self, device, **kwargs)
            service = client.services[0]
            client.services = [SimpleNamespace(uuid=SERVICE_UUID, characteristics=[]),
                               SimpleNamespace(uuid='other', characteristics=service.characteristics)]
            return client
    manager, _, _ = manager_factory(client=WrongService())
    with pytest.raises(BleMuseError, match='gatt_profile_mismatch'):
        connect(manager)


def test_no_stream_verification_from_gatt_connection_alone(manager_factory):
    frames = []
    manager, _, factory = manager_factory(client=FakeFactory(stream=False), on_frame=frames.append)
    with pytest.raises(BleMuseError, match='stream_start_timeout'):
        connect(manager)
    assert frames == []
    assert manager.snapshot()['bluetooth_state'] == 'error'
    assert not factory.clients[0].is_connected


@pytest.mark.parametrize(('operation', 'stage'), [
    ('notify:' + CONTROL_UUID, 'control_subscription'),
    ('write:h', 'halt'), ('write:p21', 'preset_selection'),
    ('notify:' + EEG_CHARACTERISTICS['AF7'], 'eeg_subscription_af7'),
    ('write:d', 'stream_start_command'),
])
def test_disconnect_reports_exact_initialization_operation(manager_factory, operation, stage):
    faults = []
    manager, _, factory = manager_factory(client=FakeFactory(drop=operation), on_fault=faults.append)
    with pytest.raises(BleMuseError, match='unexpected_disconnect_reconnect_required'):
        connect(manager)
    assert manager.snapshot()['disconnect_stage'] == stage
    assert manager.snapshot()['reconnect_required']
    assert faults and factory.clients[0].connect_calls == 1


def test_unexpected_disconnect_faults_without_reconnect_and_invalidates_clock(manager_factory):
    faults = []
    manager, _, factory = manager_factory(on_fault=faults.append)
    connect(manager)
    assert manager.clock_probe()['uncertainty_s'] >= .025
    client = factory.clients[0]
    def drop():
        client.is_connected = False
        client.disconnected_callback(client)
    on_loop(manager, drop)
    wait_for(lambda: manager.snapshot()['bluetooth_state'] == 'error')
    assert 'unexpected_disconnect_reconnect_required' in faults
    assert len(factory.clients) == 1 and client.connect_calls == 1
    with pytest.raises(ValueError, match='source_clock_unavailable'):
        manager.clock_probe()


def test_explicit_disconnect_stops_notifications_and_closes_thread(manager_factory):
    manager, _, factory = manager_factory()
    connect(manager)
    result = manager.disconnect()
    assert result['bluetooth_state'] == 'disconnected'
    client = factory.clients[0]
    assert client.callbacks == {} and not client.is_connected
    assert client.operations[-1] == 'disconnect'
    manager.close()
    assert not manager.thread_alive


def test_disconnect_error_is_safe_and_shutdown_still_exits_thread(manager_factory):
    manager, _, _ = manager_factory(client=FakeFactory(disconnect_error=True))
    connect(manager)
    with pytest.raises(BleMuseError, match='disconnect_failed'):
        manager.close()
    assert not manager.thread_alive


@pytest.mark.parametrize(('message', 'code'), [
    ('Bluetooth is powered off', 'bluetooth_powered_off'),
    ('Bluetooth permission denied private native traceback', 'bluetooth_permission_denied'),
])
def test_native_scan_errors_are_mapped_without_exposing_exception(manager_factory, message, code):
    scanner = FakeScanner()
    scanner.error = RuntimeError(message)
    manager, _, _ = manager_factory(scanner=scanner)
    with pytest.raises(BleMuseError) as error:
        manager.scan('session')
    assert str(error.value) == code
    assert manager.snapshot()['last_error'] == code
    assert 'native' not in json.dumps(manager.snapshot())


def test_empty_scan(manager_factory):
    manager, _, _ = manager_factory(scanner=FakeScanner(names=('Headphones',)))
    assert manager.scan('session') == {'devices': []}
    assert manager.snapshot()['last_error'] == 'muse_not_found'


def test_scan_is_bounded_and_exclusive(manager_factory):
    scanner = FakeScanner()
    scanner.wait = True
    manager, _, _ = manager_factory(scanner=scanner)
    errors = []
    def run():
        try:
            manager.scan('session')
        except BleMuseError as error:
            errors.append(error.code)
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert scanner.started.wait(1)
        with pytest.raises(BleMuseError, match='operation_in_progress'):
            manager.scan('session')
    finally:
        thread.join(2)
    assert not thread.is_alive() and errors == ['scan_timeout']


def test_device_handles_are_owned_expire_and_cannot_be_reused(manager_factory):
    clock = [10.]
    manager, _, _ = manager_factory(monotonic=lambda: clock[0], scan_ttl_s=1)
    handle = manager.scan('owner')['devices'][0]['id']
    with pytest.raises(BleMuseError, match='unknown_device_id'):
        manager.connect(handle, 'other')
    with pytest.raises(BleMuseError, match='unknown_device_id'):
        manager.connect('an-arbitrary-platform-uuid', 'owner')
    clock[0] += 2
    with pytest.raises(BleMuseError, match='scan_result_expired'):
        manager.connect(handle, 'owner')
    newer = manager.scan('owner')['devices'][0]['id']
    manager.scan('owner')
    with pytest.raises(BleMuseError, match='unknown_device_id'):
        manager.connect(newer, 'owner')


def test_only_one_connection_and_no_scan_while_connected(manager_factory):
    manager, _, factory = manager_factory()
    connect(manager)
    with pytest.raises(BleMuseError, match='already_connected'):
        manager.scan('session')
    with pytest.raises(BleMuseError, match='already_connected'):
        manager.connect('anything', 'session')
    assert len(factory.clients) == 1


def test_healthy_stream_survives_more_than_30_logical_seconds_and_keepalive(manager_factory):
    clock = [100.]
    manager, _, factory = manager_factory(monotonic=lambda: clock[0])
    connect(manager)
    client = factory.clients[0]
    def produce():
        for index in range(101, 763):
            clock[0] += 12 / 256
            client.emit(index)
    on_loop(manager, produce)
    wait_for(lambda: 'write:k' in client.operations)
    status = manager.snapshot()
    assert status['time_connected_s'] > 31 and status['time_streaming_s'] > 31
    assert status['eeg_sample_count'] == 663 * 12 and status['bluetooth_state'] == 'streaming'
    assert client.is_connected and client.connect_calls == 1
    manager.disconnect()
    duration = manager.snapshot()['time_connected_s']
    clock[0] += 50
    assert manager.snapshot()['time_connected_s'] == duration


def test_partial_malformed_frames_do_not_create_samples_and_gap_is_explicit(manager_factory):
    clock, frames = [10.], []
    manager, _, factory = manager_factory(monotonic=lambda: clock[0], on_frame=frames.append)
    connect(manager)
    client = factory.clients[0]
    def packets():
        clock[0] += .05
        for name, uuid in EEG_CHARACTERISTICS.items():
            client.callbacks[uuid](None, b'bad' if name == 'AF8' else packet(101))
        clock[0] += .3
        client.emit(102)
    on_loop(manager, packets)
    assert [frame.packet_index for frame in frames] == [100, 102]
    assert frames[-1].dropped_samples == 12
    assert manager.snapshot()['malformed_packets'] == 1


def test_clock_reset_faults_and_does_not_reconnect(manager_factory):
    manager, _, factory = manager_factory()
    connect(manager)
    on_loop(manager, lambda: factory.clients[0].emit(1))
    wait_for(lambda: manager.snapshot()['last_error'] == 'packet_clock_reset')
    assert manager.snapshot()['reconnect_required']
    assert len(factory.clients) == 1


def test_close_cancels_an_active_scan_and_joins_both_owned_threads(manager_factory):
    scanner = FakeScanner()
    scanner.wait = True
    manager, _, _ = manager_factory(scanner=scanner)
    outcomes = []
    def scan():
        try:
            manager.scan('session')
        except CancelledError:
            outcomes.append('cancelled')
    request_thread = threading.Thread(target=scan)
    request_thread.start()
    assert scanner.started.wait(1)
    manager.close()
    request_thread.join(2)
    assert outcomes == ['cancelled'] and not request_thread.is_alive()
    assert not manager.thread_alive


def test_scan_cache_is_bounded(manager_factory):
    manager, _, _ = manager_factory(scanner=FakeScanner(names=tuple(f'Muse-{i}' for i in range(100))))
    assert len(manager.scan('session')['devices']) == 64
    assert len(manager._cache) == 64


def test_safe_error_code_preserves_caller_diagnostic_fallback():
    assert safe_error_code(RuntimeError('private'), fallback='diagnostic_failed') == 'diagnostic_failed'


def test_old_client_notifications_and_disconnect_callback_are_ignored_after_reconnect(manager_factory):
    manager, _, factory = manager_factory()
    connect(manager)
    old_client = factory.clients[0]
    old_callbacks = dict(old_client.callbacks)
    manager.disconnect()
    connect(manager)
    def stale_callbacks():
        for uuid in EEG_CHARACTERISTICS.values():
            old_callbacks[uuid](None, packet(101))
        old_client.disconnected_callback(old_client)
    on_loop(manager, stale_callbacks)
    assert manager.snapshot()['eeg_sample_count'] == 12
    assert manager.snapshot()['bluetooth_state'] == 'streaming'


def test_diagnostic_packet_counters_survive_fault_and_disconnect(manager_factory):
    manager, _, factory = manager_factory()
    connect(manager)
    client = factory.clients[0]
    def corrupt_then_reset():
        client.callbacks[EEG_CHARACTERISTICS['AF7']](None, b'bad')
        client.emit(1)
    on_loop(manager, corrupt_then_reset)
    wait_for(lambda: manager.snapshot()['bluetooth_state'] == 'error')
    assert manager.snapshot()['malformed_packets'] == 1
    manager.disconnect()
    assert manager.snapshot()['malformed_packets'] == 1
