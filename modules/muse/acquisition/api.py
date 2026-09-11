"""Read-only module router; capture requires the visible operator CLI."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from modules.muse.acquisition.live import health
from scenescore.contracts import validate

router = APIRouter()


@router.get("/health")
def get_health():
    return health()


@router.post("/diagnostics")
def diagnostics(record: dict):
    try:
        validate(record)
        if record["kind"] != "EEGChunk":
            raise ValueError("EEGChunk_required")
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=422, content={"code": "INVALID_RECORD", "message": str(exc), "retryable": False})
    return {"mode": record["provenance"]["source_mode"], "sequence": record["sequence"],
            "sample_count": len(record["samples"]), "quality": record["quality"],
            "device_epoch": record["device_epoch"], "host_epoch": record["host_receipt"]["epoch"],
            "device_start_s": record["device_times_s"][0], "receipt_s": record["host_receipt"]["seconds"],
            "controls": "DISARMED", "clock_alignment": "UNVERIFIED"}
