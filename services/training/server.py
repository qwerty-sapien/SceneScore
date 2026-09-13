"""Bounded authenticated loopback HTTP service and confined local static assets."""

import argparse
from collections import deque
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit

from .state import MAX_EXPORT, Workspace

MAX_BODY = 16 * 1024


class TrainingServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True
    request_queue_size = 4

    def __init__(self, address, workspace, token, web_root, origins):
        if address[0] != "127.0.0.1" or not 0 <= address[1] <= 65535:
            raise ValueError("loopback_only")
        if len(token) < 24:
            raise ValueError("startup_token_minimum_24_characters")
        self.workspace, self.token = workspace, token
        self.web_root = Path(web_root).resolve()
        self.origins = set(origins)
        if not self.origins or any(
            urlsplit(o).scheme not in {"http", "https"} or not urlsplit(o).netloc or urlsplit(o).path or "*" in o
            for o in origins
        ):
            raise ValueError("exact_origins_required")
        self.auth_lock = threading.Lock()
        self.request_times = deque(maxlen=120)
        self.startup_expiry = time.monotonic() + 600
        self.session = None
        self.session_expiry = 0
        self.capacity = threading.BoundedSemaphore(4)
        super().__init__(address, Handler)
        self.timeout = 0.2

    def process_request(self, request, client_address):
        if not self.capacity.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.capacity.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.capacity.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "SceneScoreTraining/1"
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_):
        pass  # Never log bearer tokens, EEG, consent, or labels.

    def send_json(self, value, status=200):
        payload = json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
        if len(payload) > MAX_EXPORT:
            payload, status = b'{"error":"response_exceeds_32MiB_budget"}', 413
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin in self.server.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(payload)

    def guard(self, *, mutation=False, startup=False):
        port = self.server.server_address[1]
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            raise PermissionError("host_not_allowed")
        origin = self.headers.get("Origin")
        if (mutation and origin not in self.server.origins) or (
            origin is not None and origin not in self.server.origins
        ):
            raise PermissionError("origin_not_allowed")
        if origin is None and self.headers.get("Sec-Fetch-Site") not in {None, "same-origin", "none"}:
            raise PermissionError("cross_site_request_denied")
        authorization = self.headers.get("Authorization", "")
        now = time.monotonic()
        with self.server.auth_lock:
            while self.server.request_times and now - self.server.request_times[0] >= 10:
                self.server.request_times.popleft()
            if len(self.server.request_times) >= 120:
                raise ValueError("request_rate_limit")
            self.server.request_times.append(now)
            expected = self.server.token if startup else self.server.session
            expiry = self.server.startup_expiry if startup else self.server.session_expiry
            if expected is None or now >= expiry or not hmac.compare_digest(authorization, "Bearer " + expected):
                raise PermissionError("invalid_or_expired_token")
            if not startup:
                self.server.session_expiry = now + 600

    def do_OPTIONS(self):
        try:
            port = self.server.server_address[1]
            origin = self.headers.get("Origin")
            if (
                self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}
                or origin not in self.server.origins
            ):
                raise PermissionError("origin_or_host_not_allowed")
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, 403)

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, mutation):
        try:
            parsed = urlsplit(self.path)
            if len(self.path) > 2048:
                raise ValueError("request_path_too_large")
            if not parsed.path.startswith("/v1/"):
                if mutation:
                    raise ValueError("unknown_endpoint")
                return self.static(parsed.path)
            route = parsed.path[3:]
            self.guard(mutation=mutation, startup=mutation and route == "/session")
            if mutation:
                if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                    raise ValueError("bounded_JSON_body_required")
                length = int(self.headers.get("Content-Length", "0"))
                if not 2 <= length <= MAX_BODY:
                    return self.send_json({"error": "body_exceeds_16KiB_budget"}, 413)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("incomplete_body")
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError("JSON_object_required")
            else:
                body = {k: v[0] for k, v in parse_qs(parsed.query).items() if len(v) == 1}
            state = self.server.workspace
            if state.closed:
                raise ValueError("workspace_shutting_down")
            if mutation and route == "/session":
                with self.server.auth_lock:
                    if self.server.session is None or time.monotonic() >= self.server.session_expiry:
                        self.server.session = secrets.token_urlsafe(32)
                        self.server.session_expiry = time.monotonic() + 600
                    session = self.server.session
                state.touch()
                return self.send_json({"session": session, "status": state.status()})
            if not mutation and route in {"/status", "/trace"}:
                state.touch()
            if not mutation and route == "/automatic/status":
                state.automatic.touch()
            if mutation:
                handlers = {
                    "/automatic/connect": state.automatic_connect,
                    "/automatic/start": state.automatic_start,
                    "/automatic/stop": lambda _: state.automatic_stop(),
                    "/automatic/label": state.automatic.label,
                    "/connect": state.connect,
                    "/disconnect": lambda _: state.disconnect(),
                    "/record/start": state.record_start,
                    "/record/stop": lambda _: state.record_stop(),
                    "/marker": state.marker,
                    "/review": state.review,
                    "/train": lambda _: state.train(),
                    "/delete": state.delete,
                    "/diagnostics/monitor": state.diagnostics.monitor,
                    "/diagnostics/check": state.diagnostics.check_now,
                }
            else:
                handlers = {
                    "/automatic/status": lambda _: state.automatic_status(),
                    "/automatic/checkpoints": lambda _: state.automatic.store.summaries(),
                    "/status": lambda _: state.status(),
                    "/diagnostics": lambda _: state.diagnostics.snapshot(),
                    "/sources": lambda _: state.sources.discover(),
                    "/trace": lambda _: state.trace(),
                    "/review": lambda b: state.review_get(b["session_id"]),
                    "/segment": lambda b: state.segment(b["session_id"], float(b["start_s"]), float(b["end_s"])),
                    "/export": lambda b: state.raw(b["session_id"]),
                    "/model": lambda _: self.model(),
                }
            if route not in handlers:
                return self.send_json({"error": "unknown_endpoint"}, 404)
            self.send_json(handlers[route](body))
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, 403)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass
        except (ImportError, RuntimeError, OSError) as exc:
            self.send_json({"error": str(exc)}, 503)

    def model(self):
        with self.server.workspace.lock:
            if self.server.workspace.model is None:
                raise ValueError("no_local_model")
            return self.server.workspace.model

    def static(self, route):
        port = self.server.server_address[1]
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            raise PermissionError("host_not_allowed")
        path = unquote(route)
        parts = Path(path.lstrip("/")).parts
        if any(part.startswith(".") for part in parts) or "\\" in path or "\x00" in path:
            raise PermissionError("static_path_not_allowed")
        target = (self.server.web_root / (path.lstrip("/") or "index.html")).resolve()
        if (
            not target.is_relative_to(self.server.web_root)
            or not target.is_file()
            or target.stat().st_size > MAX_EXPORT
        ):
            return self.send_json({"error": "static_file_unavailable"}, 404)
        if any(part.startswith(".") for part in target.relative_to(self.server.web_root).parts):
            raise PermissionError("static_path_not_allowed")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument("--data-root", type=Path, default=Path("private_data/02A/training-web"))
    parser.add_argument("--web-root", type=Path, default=Path("artifacts/training-dist"))
    parser.add_argument("--origin", action="append")
    parser.add_argument("--token", default=os.environ.get("SCENESCORE_TRAINING_TOKEN"))
    parser.add_argument("--synthetic-rehearsal", action="store_true", help="Explicit synthetic trainer; no real accuracy evidence")
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535:
        parser.error("runtime must be1..3600seconds; port1024..65535")
    token = args.token or secrets.token_urlsafe(32)
    origin = f"http://127.0.0.1:{args.port}"
    workspace = Workspace(args.data_root)
    workspace.automatic.synthetic = args.synthetic_rehearsal
    server = TrainingServer(("127.0.0.1", args.port), workspace, token, args.web_root, args.origin or [origin])
    print(
        json.dumps(
            {
                "url": origin + "/#token=" + token,
                "pid": os.getpid(),
                "runtime_seconds": args.seconds,
                "recording": False,
                "source_started": False,
                "token_lifetime_seconds": 600,
            }
        ),
        flush=True,
    )
    end = time.monotonic() + args.seconds
    try:
        while time.monotonic() < end:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        workspace.close()
        server.server_close()
    return 0
