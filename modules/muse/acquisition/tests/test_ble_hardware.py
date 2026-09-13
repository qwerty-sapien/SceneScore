"""Explicitly opt-in real hardware checks, excluded from ordinary fixture runs."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.hardware
@pytest.mark.skipif(os.environ.get('MUSE_BLE_HARDWARE') != '1', reason='real Muse hardware diagnostic is opt-in')
def test_plain_muse_hardware_connection():
    result = subprocess.run([sys.executable, str(ROOT / 'tools/muse_ble_diagnose.py'),
                             '--name', os.environ.get('MUSE_BLE_NAME', 'Muse-AD3C'), '--seconds', '30'],
                            cwd=ROOT, capture_output=True, text=True, timeout=65)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"cleanup": "PASS"' in result.stdout


@pytest.mark.hardware
@pytest.mark.skipif(os.environ.get('MUSE_BLE_STREAM_HARDWARE') != '1', reason='real EEG streaming requires opt-in and consent')
def test_muse_hardware_streaming():
    consent = os.environ.get('MUSE_LIVE_CONSENT')
    if not consent:
        pytest.skip('MUSE_LIVE_CONSENT local file is required; no consent is fabricated')
    result = subprocess.run([sys.executable, str(ROOT / 'tools/muse_ble_diagnose.py'),
                             '--name', os.environ.get('MUSE_BLE_NAME', 'Muse-AD3C'), '--seconds', '30',
                             '--stage', 'stream', '--live-consent', consent],
                            cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"hardware_verified": true' in result.stdout
    assert '"cleanup": "PASS"' in result.stdout
