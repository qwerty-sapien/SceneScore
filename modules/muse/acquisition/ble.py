"""Bounded classic-Muse Bleak lifecycle on one owned asyncio loop.

No import-time Bluetooth operations, recording, or HTTP serialization of EEG.
Callbacks receive local frames; snapshot contains only transport diagnostics.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
import math
import re
import secrets
import threading
import time

from modules.muse.acquisition.ble_clock import BLEClock
from modules.muse.acquisition.muse_protocol import (
    ATHENA_UUID, SERVICE_UUID, CONTROL_UUID, EEG_CHARACTERISTICS, FrameAssembler, ProtocolError,
    encode_command, validate_classic_profile,
)

SAFE_ERRORS = frozenset({
    'bluetooth_powered_off', 'bluetooth_permission_denied', 'scan_timeout',
    'muse_not_found', 'scan_result_expired', 'unknown_device_id',
    'already_connected', 'operation_in_progress', 'connect_timeout',
    'gatt_profile_mismatch', 'unsupported_athena_profile',
    'stream_configuration_failed', 'stream_start_timeout',
    'malformed_eeg_packet', 'packet_clock_reset',
    'unexpected_disconnect_reconnect_required', 'disconnect_failed',
    'stream_timeout_reconnect_required', 'bluetooth_unavailable',
    'manager_closed', 'invalid_session_id', 'invalid_device_id',
})


class BleMuseError(ValueError):
    def __init__(self, code):
        self.code = code if code in SAFE_ERRORS else 'stream_configuration_failed'
        super().__init__(self.code)


def safe_error(error, fallback):
    """Native exception text is examined locally and never returned to HTTP."""
    code = getattr(error, 'code', None)
    if code in SAFE_ERRORS:
        return code
    message = str(error).lower()
    if any(term in message for term in ('powered off', 'poweredoff', 'bluetooth is off')):
        return 'bluetooth_powered_off'
    if any(term in message for term in ('not authorized', 'unauthorized', 'permission', 'access denied')):
        return 'bluetooth_permission_denied'
    return fallback


def safe_error_code(error, fallback='bluetooth_unavailable'):
    return safe_error(error, fallback)


def muse_name(name):
    """Accept a small printable Muse name, without leaking backend identifiers."""
    return name if isinstance(name, str) and re.fullmatch(r'Muse(?:[- ][A-Za-z0-9 _-]{1,48})?', name) else None


class BleMuseManager:
    """Synchronous request facade; all scanner/client methods run on one loop.

    scanner_factory accepts the BleakScanner class or an object with async
    discover(timeout=..., return_adv=True). client_factory has BleakClient's
    constructor shape. Inject monotonic only for logical-time unit fixtures.
    """

    def __init__(self, *, on_begin=None, on_frame=None, on_fault=None, on_discontinuity=None,
                 scanner_factory=None, client_factory=None, monotonic=time.monotonic,
                 scan_timeout_s=8.0, connect_timeout_s=10.0, stream_timeout_s=5.0,
                 scan_ttl_s=60.0, stage_delay_s=.1, keepalive_s=10.0):
        for value in (scan_timeout_s, connect_timeout_s, stream_timeout_s, scan_ttl_s, keepalive_s):
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 120:
                raise ValueError('bounded_ble_timeout_required')
        if not 0 <= stage_delay_s <= 1:
            raise ValueError('bounded_ble_stage_delay_required')
        self._scanner_factory, self._client_factory = scanner_factory, client_factory
        self._on_begin = on_begin or (lambda name: None)
        self._on_frame = on_frame or (lambda frame: None)
        self._on_fault = on_fault or (lambda code: None)
        self._on_discontinuity = on_discontinuity or (lambda code: None)
        self._now = monotonic
        self.scan_timeout_s, self.connect_timeout_s = scan_timeout_s, connect_timeout_s
        self.stream_timeout_s, self.scan_ttl_s = stream_timeout_s, scan_ttl_s
        self.stage_delay_s, self.keepalive_s = stage_delay_s, keepalive_s
        self.clock = BLEClock()
        self._assembler = FrameAssembler()
        self._lock, self._operation = threading.RLock(), threading.Lock()
        self._cache = {}
        self._client = None
        self._classic_verified = False
        self._notifications = []
        self._monitor_task = None
        self._cleanup_task = None
        self._first_frame = None
        self._intentional_disconnect = False
        self._closed = False
        self._closing = False
        self._active_task = None
        self._started_s = self._streaming_s = self._last_packet_s = None
        self._notification_count = self._frame_count = self._sample_count = 0
        self._connected_duration_s = self._stream_duration_s = 0.
        self._frozen_counts = {}
        self._state = {'transport': 'bleak', 'bluetooth_state': 'idle', 'device_name': None,
                       'ble_connected': False, 'reconnect_required': False,
                       'last_error': None, 'last_operation': None, 'disconnect_stage': None}
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name='scenescore-muse-ble', daemon=False)
        self._thread.start()
        if not self._ready.wait(2):
            raise RuntimeError('ble_loop_start_failed')

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._writes = asyncio.Lock()
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    @property
    def thread_alive(self):
        return self._thread.is_alive()

    def _set(self, **fields):
        with self._lock:
            self._state.update(fields)

    def snapshot(self):
        with self._lock:
            now = self._now()
            connected_s = max(0., now - self._started_s) if self._started_s is not None else self._connected_duration_s
            streaming_s = max(0., now - self._streaming_s) if self._streaming_s is not None else self._stream_duration_s
            return dict(self._state, time_connected_s=connected_s, time_streaming_s=streaming_s,
                        notification_count=self._notification_count, packet_count=self._frame_count,
                        eeg_sample_count=self._sample_count,
                        notification_rate_hz=self._notification_count / streaming_s if streaming_s else 0.,
                        packet_rate_hz=self._frame_count / streaming_s if streaming_s else 0.,
                        last_packet_age_s=max(0., now - self._last_packet_s) if self._last_packet_s is not None else None,
                        dropped_samples=self._frozen_counts.get('dropped_samples', 0) + self._assembler.dropped_samples,
                        malformed_packets=self._frozen_counts.get('malformed_packets', 0) + self._assembler.malformed_packets,
                        rejected_packets=self._frozen_counts.get('rejected_packets', 0) + self._assembler.rejected_packets,
                        buffered_frames=self._assembler.buffered_frames)

    def clock_probe(self):
        with self._lock:
            return self.clock.probe(self._now())

    def _request(self, factory, timeout):
        if self._closed or self._closing:
            raise BleMuseError('manager_closed')
        if not self._operation.acquire(blocking=False):
            raise BleMuseError('operation_in_progress')
        completed = threading.Event()
        async def execute():
            self._active_task = asyncio.current_task()
            try:
                return await factory()
            finally:
                self._active_task = None
                completed.set()
        try:
            future = asyncio.run_coroutine_threadsafe(execute(), self._loop)
            try:
                return future.result(timeout)
            except FutureTimeout:
                future.cancel()
                completed.wait(8)
                raise BleMuseError('connect_timeout') from None
        finally:
            self._operation.release()

    def scan(self, session_id):
        return self._request(lambda: self._scan(session_id), self.scan_timeout_s + 3)

    def connect(self, device_id, session_id):
        return self._request(lambda: self._connect_bounded(device_id, session_id), 24)

    def disconnect(self):
        return self._request(self._disconnect, 8)

    @staticmethod
    def _session(session_id):
        if not isinstance(session_id, str) or not 1 <= len(session_id) <= 128:
            raise BleMuseError('invalid_session_id')

    async def _scan(self, session_id):
        self._session(session_id)
        if self._client is not None:
            raise BleMuseError('already_connected')
        self._set(bluetooth_state='scanning', last_operation='scan', last_error=None)
        # A rescan invalidates prior handles. The cache is bounded to 64 devices.
        self._cache.clear()
        try:
            scanner = self._scanner_factory
            if scanner is None:
                from bleak import BleakScanner
                scanner = BleakScanner
            found = await asyncio.wait_for(
                scanner.discover(timeout=self.scan_timeout_s, return_adv=True),
                # Bleak's timeout covers its discovery sleep only. Native
                # scanner startup/shutdown need their own bounded allowance.
                self.scan_timeout_s + 2)
            candidates = []
            for device, advertisement in list(found.values())[:512]:
                name = muse_name(getattr(advertisement, 'local_name', None)) or muse_name(getattr(device, 'name', None))
                if name is None:
                    continue
                identifier = secrets.token_urlsafe(24)
                self._cache[identifier] = (session_id, self._now() + self.scan_ttl_s, device, name)
                candidates.append({'id': identifier, 'name': name})
                if len(candidates) == 64:
                    break
            self._set(bluetooth_state='idle', last_error=None if candidates else 'muse_not_found')
            return {'devices': candidates}
        except Exception as error:
            code = safe_error(error, 'scan_timeout' if isinstance(error, asyncio.TimeoutError) else 'bluetooth_unavailable')
            self._set(bluetooth_state='error', last_error=code)
            raise BleMuseError(code) from None

    async def _connect(self, device_id, session_id):
        self._session(session_id)
        if not isinstance(device_id, str) or not 1 <= len(device_id) <= 128:
            raise BleMuseError('invalid_device_id')
        if self._client is not None:
            raise BleMuseError('already_connected')
        entry = self._cache.get(device_id)
        if entry is None or entry[0] != session_id:
            raise BleMuseError('unknown_device_id')
        if self._now() > entry[1]:
            self._cache.pop(device_id, None)
            raise BleMuseError('scan_result_expired')
        _, _, device, name = entry
        self._cache.clear()
        self._assembler.reset()
        self._frozen_counts = {}
        self._classic_verified = False
        with self._lock:
            self.clock.reset()
            self._notification_count = self._frame_count = self._sample_count = 0
            self._connected_duration_s = self._stream_duration_s = 0.
            self._started_s = self._streaming_s = self._last_packet_s = None
        self._intentional_disconnect = False
        self._set(bluetooth_state='connecting', device_name=name, ble_connected=False,
                  reconnect_required=False, last_error=None, disconnect_stage=None, last_operation='connect')
        try:
            self._on_begin(name)
            factory = self._client_factory
            if factory is None:
                from bleak import BleakClient
                factory = BleakClient
            self._client = factory(device, disconnected_callback=self._disconnected_callback)
            await asyncio.wait_for(self._client.connect(), self.connect_timeout_s)
            self._assert_connected()
            self._started_s = self._now()
            self._set(bluetooth_state='gatt_verifying', ble_connected=True, last_operation='gatt_inspection')
            services = list(self._client.services)
            characteristics = [c.uuid for s in services if s.uuid.lower() == SERVICE_UUID for c in s.characteristics]
            if any(c.uuid.lower() == ATHENA_UUID for s in services for c in s.characteristics):
                characteristics.append(ATHENA_UUID)
            validate_classic_profile([s.uuid for s in services], characteristics)
            self._classic_verified = True
            self._set(bluetooth_state='configuring', last_operation='control_subscription')
            await self._subscribe(CONTROL_UUID, self._control_notification)
            await self._pause()
            await self._write('h', 'halt')
            await self._pause()
            await self._write('p21', 'preset_selection')
            await self._pause()
            self._set(bluetooth_state='subscribing')
            for channel, characteristic in EEG_CHARACTERISTICS.items():
                self._set(last_operation='eeg_subscription_' + channel.lower())
                await self._subscribe(characteristic, self._notification_for(channel))
                await self._pause()
            self._first_frame = self._loop.create_future()
            self._set(bluetooth_state='starting_stream')
            await self._write('d', 'stream_start_command')
            self._monitor_task = asyncio.create_task(self._monitor())
            await asyncio.wait_for(asyncio.shield(self._first_frame), self.stream_timeout_s)
            self._assert_connected()
            self._set(bluetooth_state='streaming', last_operation='first_eeg_packet')
            return self.snapshot()
        except asyncio.CancelledError:
            await self._fail('connect_timeout')
            raise
        except Exception as error:
            fallback = ('connect_timeout' if self._state['bluetooth_state'] == 'connecting'
                        else 'stream_start_timeout' if isinstance(error, asyncio.TimeoutError)
                        and self._state['bluetooth_state'] == 'starting_stream'
                        else 'stream_configuration_failed')
            code = safe_error(error, fallback)
            await self._fail(code)
            raise BleMuseError(code) from None
        finally:
            if self._first_frame is not None:
                if self._first_frame.done() and not self._first_frame.cancelled():
                    self._first_frame.exception()  # retrieve a callback fault even if a write failed first
                else:
                    self._first_frame.cancel()
                self._first_frame = None

    async def _connect_bounded(self, device_id, session_id):
        # Includes all staged GATT operations, then allows <=5.5s bounded cleanup
        # on cancellation. The ordinary request completes within the UI's 25s.
        try:
            return await asyncio.wait_for(self._connect(device_id, session_id),
                                          min(17., self.connect_timeout_s + self.stream_timeout_s + 2.))
        except asyncio.TimeoutError:
            raise BleMuseError('connect_timeout') from None

    def _assert_connected(self):
        if self._client is None or not self._client.is_connected:
            raise BleMuseError('unexpected_disconnect_reconnect_required')

    async def _pause(self):
        await asyncio.sleep(self.stage_delay_s)
        self._assert_connected()

    async def _subscribe(self, uuid, callback):
        await asyncio.wait_for(self._client.start_notify(uuid, callback), 2)
        self._notifications.append(uuid)
        self._assert_connected()

    async def _write(self, command, operation):
        async with self._writes:
            self._assert_connected()
            self._set(last_operation=operation)
            await asyncio.wait_for(self._client.write_gatt_char(CONTROL_UUID, encode_command(command), response=False), 2)
            self._assert_connected()

    def _control_notification(self, _sender, _data):
        # Control subscription is required by the classic protocol. Replies are
        # neither EEG nor proof of contact/quality and are intentionally not logged.
        pass

    def _notification_for(self, channel):
        client = self._client
        def notify(_sender, data):
            # Bleak normally calls on its owner loop; injection/platform callbacks
            # are still marshalled here to preserve a single decoder/clock owner.
            if threading.current_thread() is self._thread:
                self._notification(client, channel, bytes(data))
            elif not self._closed and not self._closing:
                self._loop.call_soon_threadsafe(self._notification, client, channel, bytes(data))
        return notify

    def _notification(self, client, channel, data):
        if client is not self._client or self._state['bluetooth_state'] not in ('starting_stream', 'streaming'):
            return
        received = self._now()
        self._notification_count += 1
        try:
            frames = self._assembler.add(channel, data, received)
            for frame in frames:
                self._consume_frame(frame)
        except ProtocolError as error:
            if error.code == 'out_of_order_packet':
                return
            if error.code == 'malformed_eeg_packet':
                self._set(last_error=error.code)
                self._on_discontinuity(error.code)
                return  # absent invalid channel is accounted as a gap by assembly
            self._schedule_failure(safe_error(error, 'packet_clock_reset'))
        except Exception as error:
            self._schedule_failure(safe_error(error, 'stream_configuration_failed'))

    def _consume_frame(self, frame):
        with self._lock:
            self.clock.observe(frame.device_times_s[-1], frame.first_receipt_s)
        self._on_frame(frame)
        self._frame_count += 1
        self._sample_count += len(frame.samples_uv)
        self._last_packet_s = frame.received_monotonic_s
        if self._streaming_s is None:
            self._streaming_s = self._now()
        if self._first_frame is not None and not self._first_frame.done():
            self._first_frame.set_result(True)

    async def _monitor(self):
        next_keepalive = self._now() + self.keepalive_s
        try:
            while self._client is not None and self._client.is_connected:
                await asyncio.sleep(.1)
                for frame in self._assembler.expire(self._now()):
                    self._consume_frame(frame)
                if self._last_packet_s is not None and self._now() - self._last_packet_s > .75:
                    self._schedule_failure('stream_timeout_reconnect_required')
                    return
                if self._now() >= next_keepalive:
                    # Classic Muse uses `k` for keepalive (MuseLSL Muse.keep_alive).
                    await self._write('k', 'keepalive')
                    next_keepalive = self._now() + self.keepalive_s
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._schedule_failure(safe_error(error, 'stream_configuration_failed'))

    def _disconnected_callback(self, client):
        if not self._closed and not self._closing:
            self._loop.call_soon_threadsafe(self._unexpected_disconnect, client)

    def _unexpected_disconnect(self, client):
        if client is not self._client or self._intentional_disconnect or self._closing:
            return
        self._schedule_failure('unexpected_disconnect_reconnect_required')

    def _schedule_failure(self, code):
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return
        self._mark_fault(code)
        self._cleanup_task = asyncio.create_task(self._cleanup())

    def _mark_fault(self, code):
        if self._state['bluetooth_state'] != 'error':
            self._set(disconnect_stage=self._state['last_operation'])
        self._set(bluetooth_state='error', last_error=code, ble_connected=False, reconnect_required=True)
        if self._first_frame is not None and not self._first_frame.done():
            self._first_frame.set_exception(BleMuseError(code))
        self._clear_frames()
        with self._lock:
            self.clock.reset()
        self._on_fault(code)

    def _clear_frames(self):
        for field in ('dropped_samples', 'malformed_packets', 'rejected_packets'):
            self._frozen_counts[field] = self._frozen_counts.get(field, 0) + getattr(self._assembler, field)
        self._assembler.reset()

    async def _fail(self, code):
        self._mark_fault(code)
        if self._cleanup_task is not None and not self._cleanup_task.done():
            await self._cleanup_task
        else:
            await self._cleanup()

    async def _cleanup(self):
        self._intentional_disconnect = True
        task, self._monitor_task = self._monitor_task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        client = self._client
        if client is None:
            return True
        failed = False
        if client.is_connected and self._classic_verified:
            try:
                async with self._writes:
                    await asyncio.wait_for(client.write_gatt_char(CONTROL_UUID, encode_command('h'), response=False), 1)
            except Exception:
                failed = True
        for uuid in self._notifications:
            if client.is_connected:
                try:
                    await asyncio.wait_for(client.stop_notify(uuid), .5)
                except Exception:
                    failed = True
        self._notifications.clear()
        try:
            await asyncio.wait_for(client.disconnect(), 2)
        except Exception:
            failed = True
        if client.is_connected:
            failed = True
        else:
            self._client = None
            self._classic_verified = False
            with self._lock:
                now = self._now()
                if self._started_s is not None:
                    self._connected_duration_s = max(0., now - self._started_s)
                    self._started_s = None
                if self._streaming_s is not None:
                    self._stream_duration_s = max(0., now - self._streaming_s)
                    self._streaming_s = None
        self._set(ble_connected=bool(client.is_connected))
        return not failed

    async def _disconnect(self):
        if self._cleanup_task is not None and not self._cleanup_task.done():
            if not await self._cleanup_task:
                self._set(bluetooth_state='error', last_error='disconnect_failed', reconnect_required=True)
                raise BleMuseError('disconnect_failed')
        self._set(bluetooth_state='disconnecting', last_operation='explicit_disconnect')
        self._on_fault('operator_disconnected_reconnect_required')
        with self._lock:
            self.clock.reset()
        self._clear_frames()
        okay = await self._cleanup()
        if not okay:
            self._set(bluetooth_state='error', last_error='disconnect_failed', reconnect_required=True)
            raise BleMuseError('disconnect_failed')
        self._set(bluetooth_state='disconnected', ble_connected=False, reconnect_required=False, last_error=None)
        return self.snapshot()

    async def _shutdown(self):
        if self._active_task is not None:
            task = self._active_task
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return await self._disconnect()

    def close(self):
        if self._closed:
            return
        self._closing = True
        error = None
        try:
            future = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
            try:
                future.result(16)
            except Exception as failure:
                error = failure
                future.cancel()
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(3)
            self._closed = not self._thread.is_alive()
        if not self._closed:
            raise RuntimeError('ble_thread_shutdown_failed')
        if error is not None:
            raise BleMuseError('disconnect_failed') from None
