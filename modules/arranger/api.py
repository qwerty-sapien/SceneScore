"""Unmounted phase-2 module router; no process or network at import time."""
from fastapi import APIRouter, HTTPException
from .core import Context, Policy, baseline, compile_preview

router = APIRouter()


def health():
    return {"module": "arranger", "contract": "0.1", "baseline": "available", "approval_required": True,
            "live_api_status": "NOT_RUN", "audition_status": "AUDITION_PENDING"}


@router.get("/health")
def get_health():
    return health()


@router.post("/preview")
def preview(data: dict):
    try:
        ctx = Context(**data["context"])
        policy = Policy(**data.get("policy", {}))
        brief = data.get("brief", "Original blues/ragtime swing; restrained bossa accompaniment")
        plan = baseline(ctx, policy, brief)
        return {"plan": plan, "events": compile_preview(ctx, plan, policy, brief), "mode": "manual_plan", "audition_status": "AUDITION_PENDING"}
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "invalid_arranger_input:"+type(exc).__name__) from exc
