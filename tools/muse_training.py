"""Build and open the local blink-training workspace with bounded process ownership."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600:
        parser.error("--seconds must be between 10 and 3600")
    root = Path(__file__).resolve().parents[1]
    helper = root / "artifacts/muse-bluetooth-probe"
    swift = root / "tools/muse_bluetooth.swift"
    plist = root / "tools/muse_bluetooth_info.plist"
    if sys.platform == "darwin" and shutil.which("swiftc"):
        if not helper.exists() or helper.stat().st_mtime < max(swift.stat().st_mtime, plist.stat().st_mtime):
            cache = root / "artifacts/muse-swift-cache"
            cache.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    [
                        "swiftc",
                        str(swift),
                        "-o",
                        str(helper),
                        "-module-cache-path",
                        str(cache),
                        "-Xlinker",
                        "-sectcreate",
                        "-Xlinker",
                        "__TEXT",
                        "-Xlinker",
                        "__info_plist",
                        "-Xlinker",
                        str(plist),
                    ],
                    check=True,
                    timeout=90,
                )
            except (OSError, subprocess.SubprocessError):
                print(
                    "Bluetooth metadata helper unavailable; the page will show that diagnostic limitation.", flush=True
                )
    if not args.no_build:
        subprocess.run(
            [
                str(root / "node_modules/.bin/vite"),
                "build",
                "apps/training",
                "--base",
                "./",
                "--outDir",
                "../../artifacts/training-dist",
                "--emptyOutDir",
            ],
            cwd=root,
            check=True,
            env={**os.environ, "VITE_STUDIO_URL": "https://scenescore-muse-vertical.vercel.app"},
        )
    if not (root / "artifacts/training-dist/index.html").is_file():
        parser.error("Training page is not built; omit --no-build")
    token = secrets.token_urlsafe(32)
    environment = {
        **os.environ,
        "SCENESCORE_TRAINING_TOKEN": token,
        "PYTHONPATH": os.pathsep.join(map(str, [root / "artifacts/muse-training-runtime", root, root / "src"])),
    }
    command = [
        sys.executable,
        "-m",
        "services.training",
        "--port",
        "8767",
        "--seconds",
        str(args.seconds),
        "--data-root",
        str(root / "private_data/02A/training-web"),
        "--web-root",
        str(root / "artifacts/training-dist"),
        "--origin",
        "http://127.0.0.1:8767",
        "--origin",
        "https://scenescore-muse-vertical.vercel.app",
    ]
    process = subprocess.Popen(command, cwd=root, env=environment, start_new_session=True)
    print(f"TASK JOB PID={process.pid} PGID={process.pid} PORT=8767", flush=True)
    previous_handler = signal.getsignal(signal.SIGTERM)

    def terminate(_signal, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Training service exited {process.returncode}")
            request = Request(
                "http://127.0.0.1:8767/v1/session",
                data=b"{}",
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                    "Origin": "http://127.0.0.1:8767",
                },
            )
            try:
                with urlopen(request, timeout=0.5) as response:
                    ready = json.loads(response.read(65536))
                if isinstance(ready.get("session"), str):
                    break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Training service did not become ready")
        url = "http://127.0.0.1:8767/#token=" + token
        print("Training page: http://127.0.0.1:8767 · no stream or recording starts automatically.", flush=True)
        if not args.no_open:
            webbrowser.open(url)
        else:
            print("Token is printed by the local service; paste it into the training page.", flush=True)
        process.wait(timeout=args.seconds + 15)
        if process.returncode != 0:
            raise RuntimeError(f"Training service exited {process.returncode}")
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        print(f"STOPPED PID={process.pid} exit={process.returncode}", flush=True)


if __name__ == "__main__":
    main()
