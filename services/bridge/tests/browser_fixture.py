"""Bounded SOFTWARE FIXTURE for manual browser E2E; never uses Bluetooth.

Not a production source. Serves the built studio with a permanent fixture banner
and drives the production manager through injected fake Bleak classes.
"""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import threading

from modules.muse.acquisition.ble import BleMuseManager
from modules.muse.acquisition.tests.test_ble_manager import FakeClient, FakeScanner
from services.bridge.ble_source import BleCompanionSource, ble_metadata
from services.bridge.server import BridgeServer, Companion

TOKEN = 'ble-browser-software-fixture-token-1234567890'
ROOT = Path(__file__).resolve().parents[3]
ORIGIN = 'http://127.0.0.1:8789'


class Client(FakeClient):
    async def write_gatt_char(self, uuid, data, *, response):
        await super().write_gatt_char(uuid, data, response=response)
        if data[1:-1] == b'd':
            self.emitter = asyncio.create_task(self.emit_stream())

    async def emit_stream(self):
        index = 101
        while self.is_connected:
            await asyncio.sleep(12 / 256)
            if self.is_connected:
                self.emit(index & 65535)
                index += 1

    async def disconnect(self):
        if hasattr(self, 'emitter'):
            self.emitter.cancel()
            await asyncio.gather(self.emitter, return_exceptions=True)
        await super().disconnect()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_head(self):
        if self.path in ('/', '/index.html'):
            content = (ROOT / 'artifacts/web-dist/index.html').read_text()
            banner = '<div style="position:fixed;z-index:99999;top:0;left:0;right:0;background:#ffdc65;color:#111;text-align:center">SOFTWARE FIXTURE — NO BLUETOOTH OR REAL EEG</div>'
            data = content.replace('<body>', '<body>' + banner).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            return io.BytesIO(data)
        return super().send_head()


def main():
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    companion = Companion(ble_metadata(), mode='LIVE_MUSE')
    source = BleCompanionSource(companion)
    manager = BleMuseManager(scanner_factory=FakeScanner(names=('Muse-SOFTWARE-FIXTURE',)),
                             client_factory=Client, on_begin=source.begin,
                             on_frame=source.consume_frame, on_fault=source.fault,
                             on_discontinuity=source.discontinuity)
    source.attach(manager)
    servers, threads = [], []
    try:
        servers.append(BridgeServer(companion, [ORIGIN], token=TOKEN, muse_manager=manager))
        servers.append(ThreadingHTTPServer(('127.0.0.1', 8789), partial(Handler, directory=str(ROOT / 'artifacts/web-dist'))))
        for index, server in enumerate(servers):
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .1},
                                      name=f'ble-browser-fixture-http-{index}')
            thread.start()
            threads.append(thread)
        print(json.dumps({'fixture': True, 'pid': os.getpid(), 'ports': [8766, 8789], 'lifetime_s': 600}), flush=True)
        stop.wait(600)
    finally:
        for server in servers[:len(threads)]:
            server.shutdown()
        for server in servers:
            server.server_close()
        manager.close()
        for thread in threads:
            thread.join(2)
        if manager.thread_alive or any(thread.is_alive() for thread in threads):
            raise RuntimeError('fixture_thread_did_not_exit')
        print(json.dumps({'cleanup': 'PASS', 'pid': os.getpid(), 'threads_alive': False}), flush=True)


if __name__ == '__main__':
    main()
