"""Compact local geometry views. No vertices or EEG are sent to a model."""
import json
from pathlib import Path


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def compact_summary(bundle_dir):
    return json.loads((Path(bundle_dir)/'summary.json').read_text())


def event_query(bundle_dir, event_id):
    matches=[e for e in _lines(Path(bundle_dir)/'interactions.jsonl') if e['id']==event_id]
    if len(matches)!=1:
        raise KeyError(event_id)
    return matches[0]


def state_query(bundle_dir, state_id):
    matches=[e for e in _lines(Path(bundle_dir)/'object_states.jsonl') if e['id']==state_id]
    if len(matches)!=1:
        raise KeyError(state_id)
    return matches[0]
