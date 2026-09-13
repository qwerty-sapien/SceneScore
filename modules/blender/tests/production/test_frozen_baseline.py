"""Read the immutable historical export if available; never regenerate its motion."""
import hashlib
import json
from pathlib import Path

import pytest

from modules.blender.production.validation import gap, supported_objects, tolerance

BASELINE = Path("/Users/agent/Desktop/SceneScore/artifacts/blender/validated-hero/10_projectile_tower-default/object_states.jsonl")
BASELINE_SHA256 = "a5b02fe89fee3728babf8a5b76b5583356006e9ebcfebed0bac1d62ca193a3ab"


@pytest.fixture(scope="module")
def baseline():
    if not BASELINE.is_file():
        pytest.skip("frozen historical sidecar unavailable; actual negative baseline NOT_RUN")
    assert hashlib.sha256(BASELINE.read_bytes()).hexdigest() == BASELINE_SHA256, "do not silently replace the negative reference"
    by_time = {}
    for line in BASELINE.read_text().splitlines():
        row = json.loads(line)
        by_time.setdefault(row["scene_time_s"], {})[row["object_id"]] = row
    return by_time


def physical_box(row):
    assert row["transform"]["quaternion_xyzw"] == [0, 0, 0, 1], "bounds only certify this frozen orientation"
    spec = {"shape": "box", "mode": "dynamic", "half_extents_m": [
        (hi-lo)/2 for hi, lo in zip(row["bounds_max_m"], row["bounds_min_m"])]}
    state = {**row["transform"], "scale": [1, 1, 1]}
    return spec, state


def test_actual_historical_tower_overlap_is_rejected(baseline):
    pair = ["10_projectile_tower:tower-0", "10_projectile_tower:tower-1"]
    worst, time = min((gap(*physical_box(objects[pair[0]]), *physical_box(objects[pair[1]])), t)
                      for t, objects in baseline.items())
    assert worst == pytest.approx(-.5337446928024292, abs=3e-7)
    assert time == 20.28125
    first = baseline[min(baseline)][pair[0]]
    assert worst < -100*tolerance(*physical_box(first))


def test_actual_historical_unsupported_ending_is_rejected(baseline):
    final = baseline[max(baseline)]
    specs, states = {}, {}
    # Floor position is frozen source-audit evidence, not inferred from a render.
    specs["visual-floor"] = {"shape": "box", "mode": "passive", "half_extents_m": [100, 100, .01]}
    states["visual-floor"] = {"position_m": [0, 0, -1.11], "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]}
    for oid, row in final.items():
        if ":tower-" in oid:
            specs[oid], states[oid] = physical_box(row)
        else:
            specs[oid] = {"shape": "sphere", "mode": "dynamic", "radius_m": .5}
            states[oid] = {**row["transform"], "scale": [1, 1, 1]}
    assert supported_objects(specs, states) == {"visual-floor"}
    projectile = final["10_projectile_tower:projectile"]
    assert projectile["bounds_min_m"][2]-(-1.1) == pytest.approx(1.6)
    assert all(row["bounds_min_m"][2]-(-1.1) >= 1.099999 for oid, row in final.items() if ":tower-" in oid)
