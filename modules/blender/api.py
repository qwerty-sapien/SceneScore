"""Read-only local scene views; rendering is a bounded explicit CLI operation."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from modules.blender.summary import compact_summary, event_query, state_query

router=APIRouter()
ARTIFACT_ROOT=Path(__file__).resolve().parents[2]/'artifacts/blender'


def health():
    binary=os.environ.get('BLENDER_BIN')
    return dict(status='available' if binary and Path(binary).is_file() else 'unavailable',
                reason='BLENDER_BIN path exists; runtime unverified' if binary and Path(binary).is_file()
                else 'Set BLENDER_BIN to a verified local Blender executable; summary queries do not need Blender',
                render='explicit bounded CLI only',summary_version='blender-summary-1')


@router.get('/health')
def get_health():
    return health()


def scope(bundle):
    path=(ARTIFACT_ROOT/bundle).resolve()
    if not path.is_relative_to(ARTIFACT_ROOT.resolve()) or not path.is_dir():
        raise HTTPException(404,detail={'code':'bundle_not_found','message':'Unknown local bundle','retryable':False})
    return path


@router.get('/summary')
def get_summary(bundle: str):
    try:
        return compact_summary(scope(bundle))
    except (FileNotFoundError,ValueError):
        raise HTTPException(404,detail={'code':'summary_not_found','message':'Export summary unavailable','retryable':False})


@router.get('/event')
def get_event(bundle: str, event_id: str):
    try:
        return event_query(scope(bundle),event_id)
    except (FileNotFoundError,KeyError):
        raise HTTPException(404,detail={'code':'event_not_found','message':'Exact event unavailable','retryable':False})


@router.get('/state')
def get_state(bundle: str, state_id: str):
    try:
        return state_query(scope(bundle),state_id)
    except (FileNotFoundError,KeyError):
        raise HTTPException(404,detail={'code':'state_not_found','message':'Exact state unavailable','retryable':False})
