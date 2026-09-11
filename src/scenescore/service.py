"""Loopback authoring module routes; no import-time capture, render or model jobs."""
import json
from fastapi import FastAPI, HTTPException, WebSocket
from .contracts import ROOT, validate
from .registry import Registry, CapabilityError

from modules.muse.acquisition.api import router as muse_router
from modules.blender.api import router as scene_router
from modules.music.api import router as music_router
from modules.arranger.api import router as arranger_router

app = FastAPI(title="SceneScore local authoring modules", docs_url=None, redoc_url=None)
app.include_router(muse_router, prefix="/muse")
app.include_router(scene_router, prefix="/scene")
app.include_router(music_router, prefix="/music")
app.include_router(arranger_router, prefix="/arranger")
registry = Registry()


@app.get("/health")
def health():
    return {"status": "ok", "phase": "2-wave", "mode": "local_authoring_modules", "contract_version": "0.1"}


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
