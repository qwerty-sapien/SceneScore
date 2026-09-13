"""Resolve local executables without installing tools or launching a process."""
import os
from pathlib import Path
import shutil


def resolve_executable(name, explicit=None, *, env_var=None, candidates=(), required=True):
    """Explicit argument > environment > PATH > platform locations.

    A broken explicit override is an error, never permission to use another tool.
    Resolve symlinks so Blender can locate resources beside its real executable.
    Discovery establishes executability, not a tested runtime/version.
    """
    env_var = env_var or name.upper() + '_BIN'
    override = explicit if explicit is not None else os.environ.get(env_var)

    def locate(value):
        if not value:
            return None
        path = Path(value).expanduser()
        if not path.is_file():
            found = shutil.which(str(value))
            if not found:
                return None
            path = Path(found)
        return str(path.resolve()) if path.is_file() and os.access(path, os.X_OK) else None

    if override is not None:
        found = locate(override)
        if not found:
            raise FileNotFoundError(f'{env_var}/explicit {name} is not executable: {override!r}')
        return found
    for candidate in (shutil.which(name), *candidates):
        if found := locate(candidate):
            return found
    if required:
        raise FileNotFoundError(f'{name} unavailable; set {env_var} or add it to PATH')
    return None


def blender_executable(explicit=None, *, required=True):
    return resolve_executable('blender', explicit,
                              candidates=('/Applications/Blender.app/Contents/MacOS/Blender',),
                              required=required)
