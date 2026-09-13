"""Bounded, no-recording Muse BLE hardware diagnostic. Never prints EEG or tokens.

Default is the original plain connection regression: name scan, GATT listing,
30-second hold, explicit disconnect. Other stages isolate notification setup.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]


def report(**fields):
    print(json.dumps(fields, allow_nan=False), flush=True)


def consent_ok(path):
    if path is None or not path.is_file() or path.stat().st_size > 65536:
        return False
    value = json.loads(path.read_text())
    return (isinstance(value, dict) and value.get('live_processing') is True
            and value.get('raw_recording') is False
            and isinstance(value.get('participant_statement'), str)
            and bool(value['participant_statement'].strip()))


async def plain(args):
    from bleak import BleakClient, BleakScanner
    from modules.muse.acquisition.muse_protocol import CONTROL_UUID, EEG_CHARACTERISTICS, validate_classic_profile
    stage, operation = 'scanning', 'name_scan'
    disconnected = asyncio.Event()
    expected = False
    client = None
    subscriptions = []
    counts = {'notifications': 0}

    def notification(_sender, _data):
        counts['notifications'] += 1  # Payload is discarded, never printed or saved.

    def on_disconnect(_client):
        disconnected.set()
        if not expected:
            report(result='FAIL', error='unexpected_disconnect_reconnect_required',
                   disconnect_stage=stage, last_operation=operation)

    try:
        report(stage=stage, name=args.name, recording=False)
        device = await BleakScanner.find_device_by_name(args.name, timeout=15)
        if device is None:
            report(result='BLOCKED', error='muse_not_found', stage=stage)
            return 2
        stage, operation = 'connecting', 'plain_connect'
        report(stage=stage, name=args.name)
        client = BleakClient(device, disconnected_callback=on_disconnect, timeout=12)
        await asyncio.wait_for(client.connect(), 15)
        if not client.is_connected:
            raise ValueError('unexpected_disconnect_reconnect_required')
        connected_at = time.monotonic()
        services = [service.uuid for service in client.services]
        characteristics = [char.uuid for service in client.services for char in service.characteristics]
        report(stage='gatt_verifying', services=services, characteristics=characteristics)
        validate_classic_profile(services, characteristics)
        if args.stage != 'plain':
            stage, operation = 'subscribing', 'control_subscription'
            await asyncio.wait_for(client.start_notify(CONTROL_UUID, notification), 3)
            subscriptions.append(CONTROL_UUID)
        if args.stage in ('one-eeg', 'all-eeg'):
            uuids = list(EEG_CHARACTERISTICS.values())
            for uuid in uuids[:1] if args.stage == 'one-eeg' else uuids:
                operation = 'eeg_subscription_' + uuid[:8]
                await asyncio.wait_for(client.start_notify(uuid, notification), 3)
                subscriptions.append(uuid)
        stage = 'holding_' + args.stage
        held_at = time.monotonic()
        report(stage=stage, hold_seconds=args.seconds)
        while time.monotonic() - held_at < args.seconds:
            if disconnected.is_set() or not client.is_connected:
                raise ValueError('unexpected_disconnect_reconnect_required')
            await asyncio.sleep(min(.1, max(0, args.seconds - (time.monotonic() - held_at))))
        report(result='PASS', stage=stage, measured_hold_s=time.monotonic() - held_at,
               measured_connected_s=time.monotonic() - connected_at, **counts)
        return 0
    finally:
        expected = True
        stage = 'disconnecting'
        if client is not None:
            for uuid in subscriptions:
                if client.is_connected:
                    try:
                        await asyncio.wait_for(client.stop_notify(uuid), 2)
                    except Exception:
                        pass
            await asyncio.wait_for(client.disconnect(), 5)
            if client.is_connected:
                raise ValueError('disconnect_failed')
            report(stage='disconnected', cleanup='PASS')


def streaming(args):
    from modules.muse.acquisition.ble import BleMuseManager
    from services.bridge.ble_source import BleCompanionSource, ble_metadata
    from services.bridge.server import Companion
    companion = Companion(ble_metadata(), mode='LIVE_MUSE')
    source = BleCompanionSource(companion, None)
    manager = BleMuseManager(on_begin=source.begin, on_frame=source.consume_frame,
                             on_fault=source.fault, on_discontinuity=source.discontinuity)
    source.attach(manager)
    companion.transport_status_probe = manager.snapshot
    try:
        report(stage='scanning', recording=False)
        devices = manager.scan('local-hardware-diagnostic')['devices']
        device = next((item for item in devices if item['name'] == args.name), None)
        if device is None:
            report(result='BLOCKED', error='muse_not_found')
            return 2
        manager.connect(device['id'], 'local-hardware-diagnostic')
        start, initial_count = time.monotonic(), companion.sample_count
        while time.monotonic() - start < args.seconds:
            state = companion.status()
            if not state['connected'] or not state['hardware_verified']:
                report(result='FAIL', **state)
                return 1
            time.sleep(.2)
        if companion.sample_count <= initial_count:
            raise ValueError('stream_start_timeout')
        report(result='PASS', measured_streaming_hold_s=time.monotonic() - start,
               **companion.status(), clock=companion.clock())
        return 0
    finally:
        manager.close()
        report(stage='disconnected', cleanup='PASS', ble_thread_alive=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='Muse-AD3C', help='Exact human-facing advertised Muse name')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--stage', choices=['plain', 'control', 'one-eeg', 'all-eeg', 'stream'], default='plain')
    parser.add_argument('--live-consent', type=Path, help='Required for EEG streaming; existing local no-recording consent')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 120:
        parser.error('seconds must be finite and between 1 and 120')
    if not args.name.startswith('Muse') or not 1 <= len(args.name) <= 64 or not args.name.isprintable():
        parser.error('a bounded, printable Muse name is required')
    if args.stage == 'stream' and not consent_ok(args.live_consent):
        parser.error('--stage stream requires explicit --live-consent with raw_recording:false')

    def interrupt(*_):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        return streaming(args) if args.stage == 'stream' else asyncio.run(plain(args))
    except KeyboardInterrupt:
        report(result='NOT RUN', error='operator_cancelled')
        return 130
    except Exception as error:
        # Never expose platform exception text or native buffers.
        from modules.muse.acquisition.ble import safe_error_code
        report(result='FAIL', error=safe_error_code(error, 'diagnostic_failed'))
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    raise SystemExit(main())
