"""Read-only authoring catalogue router. Integrator owns mounting; no import-time work."""
from fastapi import APIRouter, HTTPException
from .catalog import build_score, get_composition, get_groove, list_catalog

router = APIRouter()


def health():
    return {'status': 'available', 'reason': 'Original symbolic catalogue and stdlib offline renderer available; AUDITION_PENDING',
            'human_audition': 'unverified', 'renderer': 'stdlib-procedural-1'}


@router.get('/health')
def read_health():
    return health()


@router.get('/catalog')
def catalog():
    return list_catalog()


def _lookup(call, *args):
    try:
        return call(*args)
    except ValueError as error:
        raise HTTPException(404, detail={'code': str(error), 'message': 'Exact catalogue entry unavailable',
                                          'retryable': False}) from error


@router.get('/compositions/{composition_id}')
def composition(composition_id: str, version: int = 1, variation: str = 'base'):
    return _lookup(get_composition, composition_id, version, variation)


@router.get('/scores/{composition_id}')
def score(composition_id: str, version: int = 1, variation: str = 'base'):
    return _lookup(build_score, composition_id, version, variation)


@router.get('/grooves/{groove_id}')
def groove(groove_id: str, version: int = 1):
    return _lookup(get_groove, groove_id, version)
