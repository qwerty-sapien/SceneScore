"""Local contract router skeleton. Does not connect a headset or start workers."""
import json
from fastapi import FastAPI, HTTPException, WebSocket
from .contracts import ROOT, validate
from .registry import Registry, CapabilityError

app = FastAPI(title="SceneScore Phase 1 harness", docs_url=None, redoc_url=None)
registry = Registry()


@app.get("/health")
def health():
    return {"status": "ok", "phase": "1", "mode": "synthetic_fixture_only", "contract_version": "0.1"}


@app.get("/capabilities")
def capabilities():
    return list(registry.entries.values())


@app.post("/contracts/validate")
def validate_record(record: dict):
    try:
        artifact = validate(record)
        return {"status": "valid", "kind": artifact["kind"], "schema_version": "0.1"}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/capabilities/run")
def run_capability(record: dict):
    try:
        return registry.run(record)
    except CapabilityError as error:
        code = 501 if str(error).startswith("NOT_IMPLEMENTED") else 422
        raise HTTPException(status_code=code, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.websocket("/ws/fixtures")
async def fixture_stream(websocket: WebSocket):
    await websocket.accept()
    record = json.loads((ROOT / "fixtures/contracts/EEGChunk.json").read_text())
    validate(record)
    await websocket.send_json(record)
    await websocket.close(code=1000)
