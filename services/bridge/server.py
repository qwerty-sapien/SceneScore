"""Authenticated local semantic bridge; raw EEG never enters HTTP responses."""
from __future__ import annotations
import argparse
import copy
import hashlib
import hmac
import json
import math
from pathlib import Path
import secrets
import threading
import time
from collections import deque
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from modules.muse.acquisition.store import manifest, replay
from modules.muse.baseline.causal import CausalBaseline, Config
from scenescore.contracts import validate

VERSION = 'muse-bridge-1'
PORT = 8766
MAX_BODY = 2048


def synthetic_metadata():
    config = Config()
    return {'kind': 'AcquisitionMetadata', 'schema_version': '0.1', 'id': 'bridge-synthetic-metadata',
            'provenance': {'source_mode': 'synthetic', 'creator': VERSION, 'tool_version': VERSION,
                           'config_hash': config.digest, 'input_hashes': [], 'seed': 1},
            'session_id': 'bridge-' + secrets.token_hex(8), 'device_model': 'synthetic-no-headset',
            'transport': 'fixture', 'sample_rate_hz': 256,
            'channels': [{'name': name, 'unit': 'uV', 'enabled': True} for name in ['AF7', 'AF8']],
            'clock_epoch': 'synthetic-' + secrets.token_hex(8), 'hardware_verified': False,
            'raw_storage': 'local_only'}


def chunk(metadata, rows, timestamps, sequence, index, host_s, host_epoch, *, quality='good', gap=0):
    return {'kind': 'EEGChunk', 'schema_version': '0.1', 'id': metadata['session_id'] + f'-{sequence}',
            'provenance': metadata['provenance'], 'session_id': metadata['session_id'],
            'sequence': sequence, 'sample_start_index': index, 'sample_rate_hz': metadata['sample_rate_hz'],
            'channels': metadata['channels'], 'device_times_s': timestamps,
            'device_epoch': metadata['clock_epoch'],
            'host_receipt': {'seconds': host_s, 'clock': 'host_monotonic', 'epoch': host_epoch},
            'samples': rows, 'dropped_samples_before': gap,
            'quality': {'state': quality, 'reason': None if quality == 'good' else 'contact_quality_unverified'}, 'imu': None}


class Companion:
    def __init__(self, metadata=None, *, mode='SYNTHETIC_TEST'):
        self.metadata = metadata or synthetic_metadata()
        validate(self.metadata)
        self.mode = mode
        self.detector = CausalBaseline(self.metadata)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.events = deque(maxlen=128)
        self.cursor = 0
        self.connected = False
        self.available = True
        self.quality = 'unverified'
        self.reason = 'waiting_for_source_samples'
        self.last_device_s = 0.0
        self.last_host_s = time.monotonic()
        self.clock_uncertainty_s = .02
        self.host_epoch = 'bridge-host-' + secrets.token_hex(8)
        self.sample_count = 0
        self.last_subscriber_s = time.monotonic()
        self.stream_verified = False
        self.quality_gate = None
        self.source_clock_probe = None
        self.source_clock_required = False

    def _emit(self, kind, **fields):
        self.cursor += 1
        self.events.append({'id': self.cursor, 'kind': kind, **fields})
        self.changed.notify_all()

    def status(self):
        with self.lock:
            if self.quality_gate is not None and self.connected:
                quality = self.quality_gate.status(time.monotonic(), self.host_epoch)
                if quality['state'] != 'good':
                    self.quality = quality['state']
                    self.reason = quality['reason'] or 'signal_quality_unavailable'
                    if self.detector.armed:
                        self.detector.reset(self.reason)
            if self.connected and time.monotonic() - self.last_host_s > .75:
                self.fault('stream_timeout_rearm_required')
            return {'version': VERSION, 'mode': self.mode, 'connected': self.connected,
                    'hardware_verified': bool(self.metadata['hardware_verified'] and self.stream_verified),
                    'quality': self.quality, 'warmup_ready': self.detector.count >= math.ceil(self.detector.rate * self.detector.config.warmup_s),
                    'armed': self.detector.armed, 'reason': self.reason, 'model_version': self.detector.version,
                    'config_hash': self.detector.config.digest, 'source_available': self.available,
                    'recording': False, 'sample_count': self.sample_count,
                    'device_epoch': self.metadata['clock_epoch'], 'host_epoch': self.host_epoch}

    def consume(self, raw):
        with self.lock:
            if self.detector.armed and time.monotonic() - self.last_subscriber_s > 1.2:
                self.detector.reset('browser_disconnect_rearm_required')
                self._emit('status', at_s=self.last_device_s, reason='browser_disconnect_rearm_required')
            self.connected = True
            self.last_device_s = raw['device_times_s'][-1]
            self.last_host_s = time.monotonic()
            self.quality = raw['quality']['state']
            candidates, gestures = self.detector.consume(raw)
            self.sample_count += len(raw['samples'])
            self.reason = self.detector.reason if self.quality == 'good' else (raw['quality']['reason'] or self.detector.reason)
            if not self.detector.armed and self.detector.count >= self.detector.rate * self.detector.config.warmup_s and self.quality == 'good':
                self.reason = 'warmup_complete_rearm_required'
            for candidate in candidates:
                self._emit('candidate', at_s=candidate['end']['seconds'], candidate_id=candidate['id'])
            for gesture in gestures:
                if gesture['status'] == 'accepted':
                    self._emit('gesture', gesture=gesture, host_dispatch_s=time.monotonic(), host_epoch=self.host_epoch)
                else:
                    self._emit('rejection', at_s=gesture['decision']['seconds'], reason=gesture['reason'])
            return candidates, gestures

    def arm(self):
        with self.lock:
            status = self.status()
            if not status['source_available'] or not status['connected']:
                raise ValueError('source_not_connected')
            if self.mode == 'LIVE_MUSE' and not status['hardware_verified']:
                raise ValueError('hardware_not_verified')
            if status['quality'] != 'good':
                raise ValueError('quality_not_verified_good')
            self.detector.arm()
            self.last_subscriber_s = time.monotonic()
            self.reason = 'armed'
            self._emit('status', at_s=self.last_device_s, reason='armed')
            return self.status()

    def disarm(self):
        with self.lock:
            self.detector.reset('operator_disarmed_rearm_required')
            self.reason = self.detector.reason
            self._emit('status', at_s=self.last_device_s, reason=self.reason)
            return self.status()

    def fault(self, reason):
        with self.lock:
            self.detector.reset(reason)
            if self.quality_gate is not None:
                self.quality_gate.reset()
            self.connected = False
            self.quality = 'unverified'
            self.reason = reason
            self._emit('status', at_s=self.last_device_s, reason=reason)

    def clock(self):
        with self.lock:
            status = self.status()
            if not status['connected']:
                raise ValueError('source_clock_unavailable')
            host = time.monotonic()
            if self.source_clock_probe is not None:
                probe = self.source_clock_probe()
                return {**probe, 'device_epoch': self.metadata['clock_epoch'],
                        'host_epoch': self.host_epoch, 'config_hash': self.detector.config.digest,
                        'source_mode': self.metadata['provenance']['source_mode']}
            if self.source_clock_required:
                raise ValueError('source_clock_unavailable')
            # Source sample anchor extrapolated only for a fresh paced stream. The full
            # packet interval is retained as uncertainty; no device/audio zero-offset fiction.
            return {'device_s': self.last_device_s + (host - self.last_host_s),
                    'device_epoch': self.metadata['clock_epoch'], 'host_s': host,
                    'host_epoch': self.host_epoch, 'uncertainty_s': self.clock_uncertainty_s,
                    'config_hash': self.detector.config.digest,
                    'source_mode': self.metadata['provenance']['source_mode']}

    def subscribe(self, cursor):
        with self.changed:
            self.last_subscriber_s = time.monotonic()
            if cursor == self.cursor:
                self.changed.wait(.4)
            overflow = bool(self.events and cursor < self.events[0]['id'] - 1)
            if overflow:
                self.detector.reset('event_buffer_overflow_rearm_required')
                self.reason = self.detector.reason
            return {'cursor': self.cursor, 'events': [event for event in self.events if event['id'] > cursor],
                    'status': self.status(), 'overflow': overflow}


def scheduled_clock_probe(started, origin=0.0):
    """Exact local replay schedule, not a reconstruction of physical capture time."""
    def probe():
        before = time.monotonic()
        after = time.monotonic()
        host = (before + after) / 2
        return {'device_s': origin + host - started, 'host_s': host,
                'uncertainty_s': (after - before) / 2,
                'method': 'explicit_local_playback_schedule'}
    return probe


def synthetic_source(companion, stop):
    rate, width, index, sequence = 256, 4, 0, 0
    start = time.monotonic()
    companion.source_clock_probe = scheduled_clock_probe(start)
    companion.clock_uncertainty_s = width / rate + .004
    while not stop.is_set():
        times = [(index + j) / rate for j in range(width)]
        rows = []
        for at in times:
            phase = at % 8
            value = .2 * math.sin(at * 12)
            for onset in (3, 3.45):
                if onset <= phase <= onset + .18:
                    value += 180 * math.sin(math.pi * (phase - onset) / .18)
            rows.append([value, value * .97])
        target = start + times[-1]
        if stop.wait(max(0, target - time.monotonic())):
            break
        companion.clock_uncertainty_s = width / rate + max(0, time.monotonic() - target)
        companion.consume(chunk(companion.metadata, rows, times, sequence, index, time.monotonic(), companion.host_epoch))
        index, sequence = index + width, sequence + 1
    companion.source_clock_probe = None


def replay_source(companion, stop, path):
    first_time, started = None, time.monotonic()
    for raw in replay(path):
        if first_time is None:
            first_time = raw['device_times_s'][0]
            companion.source_clock_probe = scheduled_clock_probe(started, first_time)
        if stop.wait(max(0, started + raw['device_times_s'][-1] - first_time - time.monotonic())):
            companion.source_clock_probe = None
            return
        copied = copy.deepcopy(raw)
        copied['provenance'] = copy.deepcopy(companion.metadata['provenance'])
        companion.clock_uncertainty_s = len(copied['samples']) / copied['sample_rate_hz'] + max(0, time.monotonic() - (started + raw['device_times_s'][-1] - first_time))
        companion.consume(copied)
    companion.source_clock_probe = None
    companion.fault('replay_complete_rearm_required')
    companion.available = False


def live_lsl_source(companion, stop, source_id, quality_profile=None):
    """Exact verified EEG stream with calibrated signal checks, in memory only.

    These are calibrated amplitude/variance/continuity checks, not contact impedance.
    Missing or ineligible real-session calibration cannot create quality:good.
    """
    from modules.muse.runtime.quality import QualityGate
    from services.bridge.lsl_clock import LSLClock
    companion.quality_gate = QualityGate(companion.metadata, quality_profile)
    companion.source_clock_required = True
    try:
        import pylsl
    except ImportError:
        companion.available = False
        companion.fault('optional_dependency_unavailable_pylsl')
        return
    streams = pylsl.resolve_byprop('source_id', source_id, minimum=1, timeout=2)
    if len(streams) != 1:
        raise ValueError('exactly_one_verified_lsl_source_required')
    summary, metadata = streams[0], companion.metadata
    if not metadata['hardware_verified'] or metadata['transport'] != 'lsl' or metadata['provenance']['source_mode'] != 'real_device':
        raise ValueError('verified_real_device_lsl_metadata_required')
    if summary.channel_count() != len(metadata['channels']) or summary.nominal_srate() != metadata['sample_rate_hz']:
        raise ValueError('lsl_metadata_mismatch')
    inlet = pylsl.StreamInlet(summary, max_buflen=2, max_chunklen=4, recover=False)
    previous, index, sequence = None, 0, 0
    try:
        # Resolver summaries intentionally omit extended descriptors; fetch full info.
        info = inlet.info(timeout=2)
        descriptor = info.desc().child('channels').child('channel')
        for expected in metadata['channels']:
            if descriptor.child_value('label') != expected['name'] or descriptor.child_value('unit') != expected['unit']:
                raise ValueError('lsl_channel_or_unit_unverified')
            descriptor = descriptor.next_sibling()
        companion.stream_verified = True
        source_clock = LSLClock(inlet, pylsl)
        companion.source_clock_probe = source_clock.probe
        while not stop.is_set():
            if inlet.was_clock_reset():
                raise ValueError('lsl_clock_reset_reconnect_required')
            rows, times = inlet.pull_chunk(timeout=.02, max_samples=4)
            if not times:
                companion.status()
                continue
            received = time.monotonic()
            for row, at in zip(rows, times):
                if previous is not None and at <= previous:
                    raise ValueError('timestamp_reset_reconnect_required')
                gap = 0 if previous is None else max(0, round((at - previous) * metadata['sample_rate_hz']) - 1)
                raw = chunk(metadata, [row], [at], sequence, index + gap, received,
                            companion.host_epoch, quality='unverified', gap=gap)
                with companion.lock:
                    raw['quality'] = companion.quality_gate.consume(raw)
                    companion.consume(raw)
                previous, index, sequence = at, index + gap + 1, sequence + 1
    finally:
        companion.source_clock_probe = None
        inlet.close_stream()


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, companion, origins, *, token=None, port=PORT):
        self.companion, self.origins = companion, frozenset(origins)
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError('exact_browser_origin_required')
            if parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost'):
                raise ValueError('remote_origin_requires_https')
        self.token = token or secrets.token_urlsafe(32)
        self.sessions = {}
        self.session_lock = threading.Lock()
        self.capacity = threading.BoundedSemaphore(8)
        super().__init__(('127.0.0.1', port), Handler)

    def process_request(self, request, client_address):
        request.settimeout(3)
        if not self.capacity.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.capacity.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.capacity.release()


class Handler(BaseHTTPRequestHandler):
    server: BridgeServer
    protocol_version = 'HTTP/1.0'

    def log_message(self, *args):
        pass  # Credentials and requested URLs never enter access logs.

    def respond(self, code, data):
        body = json.dumps(data, separators=(',', ':'), allow_nan=False).encode()
        self.send_response(code)
        origin = self.headers.get('Origin')
        if origin in self.server.origins:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def boundary(self):
        if self.client_address[0] != '127.0.0.1' or self.headers.get('Host') != '127.0.0.1:' + str(self.server.server_port):
            self.respond(403, {'error': 'loopback_host_required'})
            return False
        if self.headers.get('Origin') not in self.server.origins:
            self.respond(403, {'error': 'origin_not_allowed'})
            return False
        if len(self.path) > 256:
            self.respond(400, {'error': 'path_too_large'})
            return False
        return True

    def do_OPTIONS(self):
        if not self.boundary():
            return
        if self.headers.get('Access-Control-Request-Method') not in ('GET', 'POST'):
            self.respond(405, {'error': 'method_not_allowed'})
            return
        requested = {v.strip().lower() for v in self.headers.get('Access-Control-Request-Headers', '').split(',') if v.strip()}
        if not requested <= {'authorization', 'content-type'}:
            self.respond(403, {'error': 'headers_not_allowed'})
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Max-Age', '60')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def authorized(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or len(auth) > 160:
            return None
        return auth[7:]

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api()

    def handle_api(self):
        if not self.boundary():
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 <= size <= MAX_BODY or self.headers.get('Transfer-Encoding'):
                raise ValueError('bounded_content_length_required')
            if self.command == 'POST':
                if self.headers.get('Content-Type') != 'application/json':
                    raise ValueError('application_json_required')
                body = json.loads(self.rfile.read(size) or b'{}')
                if body != {}:
                    raise ValueError('command_has_no_parameters')
            elif size:
                raise ValueError('get_body_not_allowed')
            parsed = urlsplit(self.path)
            auth = self.authorized()
            with self.server.session_lock:
                now = time.monotonic()
                self.server.sessions = {key: value for key, value in self.server.sessions.items() if value[0] > now}
                if parsed.path == '/v1/session' and self.command == 'POST' and not parsed.query:
                    if not auth or not hmac.compare_digest(auth, self.server.token):
                        self.respond(401, {'error': 'invalid_session_token'})
                        return
                    if len(self.server.sessions) >= 4:
                        self.respond(429, {'error': 'session_limit'})
                        return
                    session = secrets.token_urlsafe(32)
                    self.server.sessions[session] = (now + 600, self.headers['Origin'])
                    self.server.companion.disarm()
                    self.respond(200, {'session': session, 'expires_in_s': 600, 'cursor': self.server.companion.cursor, 'status': self.server.companion.status()})
                    return
                if not auth or auth not in self.server.sessions or self.server.sessions[auth][1] != self.headers['Origin']:
                    self.respond(401, {'error': 'session_expired_or_unauthenticated'})
                    return
            companion = self.server.companion
            if self.command == 'GET' and parsed.path == '/v1/status' and not parsed.query:
                result = companion.status()
            elif self.command == 'GET' and parsed.path == '/v1/events':
                query = parse_qs(parsed.query, strict_parsing=True)
                if set(query) != {'cursor'} or len(query['cursor']) != 1:
                    raise ValueError('one_cursor_required')
                cursor = int(query['cursor'][0])
                if not 0 <= cursor <= companion.cursor:
                    raise ValueError('invalid_cursor')
                result = companion.subscribe(cursor)
            elif self.command == 'POST' and not parsed.query and parsed.path in ('/v1/clock', '/v1/arm', '/v1/disarm'):
                result = {'/v1/clock': companion.clock, '/v1/arm': companion.arm, '/v1/disarm': companion.disarm}[parsed.path]()
            else:
                self.respond(404, {'error': 'unknown_command'})
                return
            self.respond(200, result)
        except (ValueError, TypeError, KeyError) as error:
            self.respond(400, {'error': str(error)[:150]})


def main():
    parser = argparse.ArgumentParser(description='Local semantic Muse companion; raw EEG is never served or recorded.')
    parser.add_argument('--source', choices=['synthetic', 'replay', 'lsl'], default='synthetic')
    parser.add_argument('--replay-session', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--lsl-source-id')
    parser.add_argument('--quality-profile', type=Path, help='Bounded calibrated signal-quality profile from eligible real sessions')
    parser.add_argument('--live-consent', type=Path, help='Local JSON consent with live_processing=true; no raw recording')
    parser.add_argument('--origin', action='append', default=[], help='Exact permitted browser origin, repeated as needed')
    parser.add_argument('--seconds', type=float, default=600, help='Bounded lifetime, at most 3600 seconds')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 3600:
        parser.error('--seconds must be in (0,3600]')
    stop = threading.Event()
    if args.source == 'replay':
        if not args.replay_session:
            parser.error('--replay-session required')
        metadata = copy.deepcopy(manifest(args.replay_session)['metadata'])
        original = metadata['provenance']['source_mode']
        metadata['provenance']['source_mode'] = 'replay' if original == 'real_device' else 'synthetic'
        metadata['provenance']['input_hashes'].append(hashlib.sha256((args.replay_session / 'manifest.json').read_bytes()).hexdigest())
        companion = Companion(metadata, mode='REAL_REPLAY' if original == 'real_device' else 'SYNTHETIC_TEST')
        source = partial(replay_source, companion, stop, args.replay_session)
    elif args.source == 'lsl':
        if not args.metadata or not args.lsl_source_id or not args.live_consent:
            parser.error('LSL requires --metadata, --lsl-source-id and --live-consent')
        consent = json.loads(args.live_consent.read_text())
        if consent.get('live_processing') is not True or consent.get('raw_recording') is not False or not consent.get('participant_statement'):
            parser.error('explicit live-processing consent statement with raw_recording:false required')
        companion = Companion(json.loads(args.metadata.read_text()), mode='LIVE_MUSE')
        profile = None
        if args.quality_profile:
            if args.quality_profile.is_symlink() or args.quality_profile.stat().st_size > 65536:
                parser.error('quality profile must be a regular local JSON file at most 65536 bytes')
            profile = json.loads(args.quality_profile.read_text())
        source = partial(live_lsl_source, companion, stop, args.lsl_source_id, profile)
    else:
        companion = Companion()
        source = partial(synthetic_source, companion, stop)
    server = BridgeServer(companion, args.origin or ['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:4173'])
    def run_source():
        try:
            source()
        except Exception as error:
            companion.available = False
            companion.fault('source_error_' + type(error).__name__)
    source_thread = threading.Thread(target=run_source, name='muse-local-source')
    http_thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .1}, name='muse-loopback-http')
    source_thread.start()
    http_thread.start()
    print(json.dumps({'listen': '127.0.0.1:8766', 'mode': companion.mode, 'token': server.token,
                      'origins': sorted(server.origins), 'lifetime_s': args.seconds, 'recording': False}), flush=True)
    try:
        stop.wait(args.seconds)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        source_thread.join(4)
        http_thread.join(4)
        if source_thread.is_alive() or http_thread.is_alive():
            raise RuntimeError('task_owned_thread_did_not_exit')
        companion.fault('companion_stopped')


if __name__ == '__main__':
    main()
