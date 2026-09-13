"""Portable discovery tests use local dummy executables; no Blender launch."""
from pathlib import Path
import sys

import pytest

from modules.blender import executables as exe


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    for name in ('BLENDER_BIN', 'FFMPEG_BIN', 'FFPROBE_BIN'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('PATH', '')


def executable(tmp_path, name):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('#!/bin/sh\nexit 0\n')
    p.chmod(0o755)
    return p


def test_override_precedence_and_space_paths(tmp_path, monkeypatch):
    selected = executable(tmp_path, 'different checkout/custom blender')
    monkeypatch.setenv('BLENDER_BIN', sys.executable)
    assert exe.blender_executable(str(selected)) == str(selected)
    assert exe.blender_executable() == str(Path(sys.executable).resolve())


@pytest.mark.parametrize('name', ['blender', 'ffmpeg', 'ffprobe'])
def test_path_discovery_and_resolved_symlink(tmp_path, monkeypatch, name):
    target = executable(tmp_path, 'tool resources/real executable')
    (tmp_path/name).symlink_to(target)
    monkeypatch.setenv('PATH', str(tmp_path))
    assert exe.resolve_executable(name) == str(target)


def test_platform_fallback_after_path(tmp_path):
    fallback = executable(tmp_path, 'Blender.app/Contents/MacOS/Blender')
    assert exe.resolve_executable('blender', candidates=[fallback]) == str(fallback)


@pytest.mark.parametrize('value', ['', 'missing', 'not-executable'])
def test_bad_override_never_falls_back(tmp_path, monkeypatch, value):
    p = tmp_path/'not-executable'
    p.write_text('data')
    monkeypatch.setenv('PATH', str(tmp_path))
    executable(tmp_path, 'blender')
    monkeypatch.setenv('BLENDER_BIN', str(p) if value == 'not-executable' else value)
    with pytest.raises(FileNotFoundError):
        exe.blender_executable()


def test_missing_tool_is_explicitly_required_or_optional():
    with pytest.raises(FileNotFoundError, match='FFMPEG_BIN'):
        exe.resolve_executable('ffmpeg')
    assert exe.resolve_executable('ffmpeg', required=False) is None


@pytest.mark.parametrize('name', ['ffmpeg', 'ffprobe'])
def test_media_environment_override(name, monkeypatch):
    monkeypatch.setenv(name.upper() + '_BIN', sys.executable)
    assert exe.resolve_executable(name) == str(Path(sys.executable).resolve())
