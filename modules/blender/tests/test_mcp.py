"""MCP synthetic protocol and relocation tests; do not require a live addon."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
from types import SimpleNamespace

import pytest

from tools.blender_mcp.client import run_calls
from tools.blender_mcp.response_guard import classify_response

ROOT = Path(__file__).resolve().parents[3]


def text(value, **extra):
    return {'isError': False, 'content': [{'type': 'text', 'text': value}], **extra}


@pytest.mark.parametrize('payload', [
    text('{"objects":[]}'),
    text('{"objects":[{"name":"ErrorCube"}]}'),
    text('Code executed successfully: completed'),
    text('Code executed successfully: '),  # Empty stdout with a real acknowledgement.
])
def test_valid_responses(payload):
    assert classify_response('execute_blender_code', payload)['status'] == 'PASSED'


@pytest.mark.parametrize('payload', [
    text('ok', isError=True),
    text('Traceback (most recent call last):\n  file.py\nValueError: bad'),
    text('Code executed successfully: Traceback (most recent call last):\nModuleNotFoundError: missing'),
    text('ModuleNotFoundError: no optional module'),
    text('Code executed successfully: No module named blender_mcp.config'),
    text('working\nError executing code: bad'),
    text('Code executed successfully: {"success": false}'),
    text('{"result":{"error":"failed"}}'),
    text('ok', structuredContent={'result': 'ModuleNotFoundError: missing'}),
    text('ok', structuredContent={'result': {'status': 'failed'}}),
    text('Error getting scene info: Could not connect to Blender.'),
    text('Rejected by safe mode: blocked'),
])
def test_recognized_execution_failures(payload):
    assert classify_response('execute_blender_code', payload)['status'] == 'FAILED'


@pytest.mark.parametrize('content', [[], [{'type': 'text', 'text': '  '}]])
def test_empty_output_policy(content):
    payload = {'isError': False, 'content': content}
    assert classify_response('execute_blender_code', payload)['status'] == 'FAILED'
    assert classify_response('execute_blender_code', payload, allow_empty=True)['status'] == 'PASSED'
    assert classify_response('get_scene_info', payload, allow_empty=True)['status'] == 'FAILED'
    assert classify_response('execute_blender_code', {**payload, 'isError': True}, allow_empty=True)['status'] == 'FAILED'


@pytest.mark.parametrize('failure', [text('ModuleNotFoundError: missing'), text('no', isError=True), TimeoutError('fixture timeout')])
def test_client_records_failure_and_stops_following_calls(tmp_path, failure):
    attempted = []
    class Session:
        async def call_tool(self, name, arguments):
            attempted.append(name)
            if isinstance(failure, Exception):
                raise failure
            return SimpleNamespace(model_dump=lambda **kwargs: failure)
    rows = []
    code = asyncio.run(run_calls(Session(), [('get_scene_info', {}), ('execute_blender_code', {})], tmp_path, rows))
    assert code == 1 and attempted == ['get_scene_info']
    assert json.loads((tmp_path/'calls.json').read_text())[0]['verdict']['status'] == 'FAILED'


def test_client_success_and_receipt(tmp_path):
    class Session:
        async def call_tool(self, name, arguments):
            return SimpleNamespace(model_dump=lambda **kwargs: text('{"objects":[]}'))
    assert asyncio.run(run_calls(Session(), [('get_scene_info', {})], tmp_path, [])) == 0
    assert json.loads((tmp_path/'calls.json').read_text())[0]['verdict']['status'] == 'PASSED'


@pytest.mark.parametrize('nested', [False, True])
def test_repository_config_survives_relocation_and_pins_safety(tmp_path, nested):
    repo = tmp_path/'a different checkout'
    launcher = repo/'tools/blender_mcp/launch.sh'
    launcher.parent.mkdir(parents=True)
    shutil.copyfile(ROOT/'tools/blender_mcp/launch.sh', launcher)
    python = repo/'artifacts/tools/blender-mcp-env/bin/python'
    python.parent.mkdir(parents=True)
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$BLENDER_HOST|$BLENDER_PORT|$BLENDER_MCP_SAFE_MODE|$DISABLE_TELEMETRY|$*"\n')
    python.chmod(0o755)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True, timeout=10)
    config = tomllib.loads((ROOT/'.codex/config.toml').read_text())['mcp_servers']['blender']
    assert config['tool_timeout_sec'] == 30
    assert set(config['enabled_tools']) == {'get_addon_status', 'get_scene_info', 'get_object_info', 'get_viewport_screenshot', 'execute_blender_code'}
    env = dict(os.environ, BLENDER_HOST='external.example', BLENDER_PORT='1', BLENDER_MCP_SAFE_MODE='0', DISABLE_TELEMETRY='false')
    env.pop('BLENDER_MCP_PYTHON', None)
    cwd = launcher.parent if nested else repo
    result = subprocess.run([config['command'], *config['args']], cwd=cwd, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '127.0.0.1|9876|1|true|-c from blender_mcp.server import main; main()'


def test_launcher_missing_override_fails_without_download(tmp_path):
    result = subprocess.run(['sh', str(ROOT/'tools/blender_mcp/launch.sh')],
                            env=dict(os.environ, BLENDER_MCP_PYTHON=str(tmp_path/'missing')),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert 'missing or not executable' in result.stderr
