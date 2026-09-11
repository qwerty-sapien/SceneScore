import copy
import json
import math
from pathlib import Path
import pytest
from scenescore.contracts import ROOT, VALIDATOR, SCHEMA, validate, load_json, content_hash, approved_payload
from scenescore.harness import FakeScheduler, classify_closed_sequence, map_clock, validate_chunks
from scenescore.registry import Registry, CapabilityError
from scenescore.cli import fixtures
from fastapi.testclient import TestClient
from scenescore.service import app

CASES = load_json(ROOT / "fixtures/manifest.json")


def f(name):
    return load_json(ROOT / "fixtures/contracts" / (name + ".json"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: Path(c["path"]).stem)
def test_shared_fixture(case):
    data = load_json(ROOT / case["path"])
    if case["valid"]:
        assert validate(data) == data
    else:
        with pytest.raises(ValueError):
            validate(data)


def test_schema_and_catalog_have_every_positive_family():
    VALIDATOR.check_schema(SCHEMA)
    catalog = load_json(ROOT / "contracts/0.1/catalog.json")
    valid_kinds = {load_json(ROOT/c["path"])["kind"] for c in CASES if c["valid"]}
    assert set(catalog["kinds"]) == valid_kinds
    assert fixtures()["status"] == "passed"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_rejected(value):
    data = f("BlinkCandidate")
    data["score"] = value
    with pytest.raises(ValueError, match="non_finite"):
        validate(data)


def test_approval_binds_exact_bytes_and_inputs():
    plan = f("ArrangementPlan")
    payload = json.dumps(plan).encode()
    approval = f("Approval")
    inputs = [plan["scene_hash"], plan["composition_hash"]]
    approval.update(approved_payload_sha256=content_hash(payload), input_hashes=inputs)
    assert approved_payload(payload, approval, inputs) == plan
    for changed, hashes in [(payload+b" ", inputs), (payload, ["b"*64, "a"*64])]:
        with pytest.raises(ValueError, match="stale_or_unapproved"):
            approved_payload(changed, approval, hashes)


def test_seed_and_parameter_cache_identity(tmp_path):
    registry = Registry(tmp_path)
    request = f("CapabilityRequest")
    request.update(capability_id="contracts.validate", input=f("SceneManifest"), output_path="artifacts/harness/out.json", timeout_s=5)
    first = registry.run(request)
    second = registry.run(request)
    assert not first["cached"] and second["cached"]
    assert first["cache_key"] == second["cache_key"]
    assert json.loads((tmp_path/request["output_path"]).read_text()) == request["input"]
    request["input"]["provenance"]["seed"] += 1
    assert registry.run(request)["cache_key"] != first["cache_key"]
    request["input"]["provenance"]["config_hash"] = "b"*64
    third = registry.run(request)
    (tmp_path/"artifacts/harness/cache"/(third["cache_key"]+".json")).write_text('{}')
    with pytest.raises(CapabilityError, match="CACHE_INTEGRITY_FAILED"):
        registry.run(request)


@pytest.mark.parametrize("change,reason", [
    ({"capability_id":"invented.tool"}, "UNKNOWN_CAPABILITY"),
    ({"output_path":"../escape.json"}, "OUTPUT_PATH_DENIED"),
    ({"output_path":"/tmp/escape.json"}, "OUTPUT_PATH_DENIED"),
    ({"output_path":"docs/escape.json"}, "OUTPUT_PATH_DENIED"),
    ({"timeout_s":11}, "BUDGET_EXCEEDED"),
])
def test_registry_preconditions(tmp_path, change, reason):
    request = f("CapabilityRequest")
    request.update(change)
    with pytest.raises(CapabilityError, match=reason):
        Registry(tmp_path).run(request)
    assert not list(tmp_path.rglob('*.json'))


def test_unimplemented_never_reports_success(tmp_path):
    with pytest.raises(CapabilityError, match="NOT_IMPLEMENTED"):
        Registry(tmp_path).run(f("CapabilityRequest"))
    assert not list(tmp_path.rglob('*.json'))


def test_registry_output_symlink_cannot_escape(tmp_path):
    root = tmp_path/"root"
    root.mkdir()
    (root/"artifacts").symlink_to(tmp_path)
    request = f("CapabilityRequest")
    request.update(capability_id="contracts.validate", timeout_s=5, output_path="artifacts/harness/out.json")
    with pytest.raises(CapabilityError, match="OUTPUT_PATH_DENIED"):
        Registry(root).run(request)


def test_registry_concurrency_guard(tmp_path):
    registry = Registry(tmp_path)
    request = f("CapabilityRequest")
    request.update(capability_id="contracts.validate", timeout_s=5, output_path="artifacts/harness/out.json")
    registry.lock.acquire()
    try:
        with pytest.raises(CapabilityError, match="CONCURRENCY_EXCEEDED"):
            registry.run(request)
    finally:
        registry.lock.release()


def test_closure_prefix_ambiguity_and_single_noop():
    for count in [1,2,3]:
        assert classify_closed_sequence(count, closed=False) == "pending"
    assert classify_closed_sequence(1) == "none"
    assert classify_closed_sequence(2) == "request_modulation"
    assert classify_closed_sequence(3) == "none"
    assert classify_closed_sequence(3,"multi_count_expression_experiment") == "toggle_approved_expression_preset"


def test_clock_epoch_offset_drift_and_validity():
    mapping = f("ClockMapping")
    assert map_clock(mapping,10,"fixture-1") == pytest.approx(20.01)
    with pytest.raises(ValueError, match="stale_clock"):
        map_clock(mapping,10,"old")
    with pytest.raises(ValueError, match="stale_clock"):
        map_clock(mapping,101,"fixture-1")


def test_duplicate_seek_late_and_unrelated_lane_preservation():
    a = f("ControlAction")
    scheduler = FakeScheduler()
    assert scheduler.submit(a,2,10) == "queued"
    assert scheduler.queue[0]["time_s"] == 2.5
    assert scheduler.queue[0]["lanes"] == a["before"]
    assert scheduler.submit(a,2,10) == "duplicate"
    another = copy.deepcopy(a)
    another["id"] = "different-id-same-sequence"
    assert scheduler.submit(another,2,10) == "duplicate"
    scheduler.reset("new-epoch",0)
    assert scheduler.queue == []
    assert scheduler.submit(a,2,10) == "stale_epoch"
    late = FakeScheduler(now=9.99)
    assert late.submit(a,2,10) == "expired_before_boundary"
    assert FakeScheduler().submit(a,2,1) == "future_or_expired"


def test_stream_duplicates_and_accounted_packet_loss():
    first = f("EEGChunk")
    with pytest.raises(ValueError, match="duplicate_or_unaccounted_gap"):
        validate_chunks([first, first])
    second = copy.deepcopy(first)
    second.update(sequence=2, sample_start_index=5, dropped_samples_before=3, device_times_s=[5/256,6/256])
    validate_chunks([first, second])
    second["dropped_samples_before"] = 0
    with pytest.raises(ValueError, match="duplicate_or_unaccounted_gap"):
        validate_chunks([first, second])


def test_api_and_websocket_are_fixture_only():
    with TestClient(app) as client:
        assert client.get('/health').json()['mode'] == 'local_authoring_modules'
        assert client.post('/contracts/validate',json=f('SceneManifest')).status_code == 200
        assert client.post('/contracts/validate',json=f('bad-units')).status_code == 422
        assert client.post('/capabilities/run',json=f('CapabilityRequest')).status_code == 501
        with client.websocket_connect('/ws/fixtures') as ws:
            assert ws.receive_json()['provenance']['source_mode'] == 'synthetic'


def test_bundle_references_and_exact_catalog_versions():
    from scenescore.contracts import validate_bundle
    bundle = [f(k) for k in ["SceneManifest", "ObjectState", "InteractionEvent", "BrushGroove", "CompositionSpec", "ArrangementPlan", "ScoreEvent"]]
    validate_bundle(bundle)
    for index, key, value in [(1, "object_id", "missing"), (4, "groove_id", "invented"), (5, "groove_version", 99), (6, "instrument_id", "unknown")]:
        changed = copy.deepcopy(bundle)
        changed[index][key] = value
        with pytest.raises(ValueError):
            validate_bundle(changed)


def test_provider_projection_shape_never_replaces_semantics():
    from jsonschema import Draft202012Validator
    projection = load_json(ROOT/"contracts/provider/arrangement-plan.schema.json")
    validator = Draft202012Validator(projection)
    plan = f("ArrangementPlan")
    validator.validate(plan)
    plan["register_min"] = 120
    plan["register_max"] = 20
    validator.validate(plan)
    with pytest.raises(ValueError, match="register_bounds"):
        validate(plan)


def test_device_epoch_change_cannot_be_replayed_as_continuity():
    a = f("EEGChunk")
    b = copy.deepcopy(a)
    b.update(device_epoch="new",sequence=1,sample_start_index=2,device_times_s=[2/256,3/256])
    with pytest.raises(ValueError, match="stream_epoch_changed"):
        validate_chunks([a,b])
