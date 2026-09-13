"""Conservative MCP call validation; no physics or animation-quality verdict."""
from __future__ import annotations

import json
import re
from typing import Any

FAILURE_PREFIX = re.compile(r'^(?:error\b|failed\b|failure\b|could not\b|cannot\b|rejected\b|no module named\b)', re.I)
EXCEPTION_TEXT = re.compile(r'Traceback \(most recent call last\)|\bModuleNotFoundError\b|\bNo module named\b|\b[A-Za-z_][\w.]*(?:Error|Exception):', re.I)
FAILURE_STATUSES = {'error', 'failed', 'failure', 'rejected'}


def _failure_reasons(value, location):
    """Inspect result envelopes, without interpreting scene object names as errors."""
    reasons = []
    if isinstance(value, str):
        text = value.strip()
        if EXCEPTION_TEXT.search(text):
            reasons.append(f'{location}: execution exception/traceback: {text[:500]}')
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, (dict, list)):
            reasons.extend(_failure_reasons(parsed, location))
        elif any(FAILURE_PREFIX.match(line.strip()) for line in text.splitlines()):
            reasons.append(f'{location}: {text[:500]}')
        elif text.startswith('Code executed successfully:'):
            # Upstream can wrap a nested failure in a success-prefixed string.
            reasons.extend(_failure_reasons(text.split(':', 1)[1], location + '.result'))
    elif isinstance(value, dict):
        if (value.get('isError') is True or value.get('error') or value.get('success') is False
                or str(value.get('status', '')).lower() in FAILURE_STATUSES):
            reasons.append(f'{location}: result reports failure')
        for key in ('result', 'output', 'text', 'stdout', 'stderr'):
            if key in value:
                reasons.extend(_failure_reasons(value[key], location + '.' + key))
    elif isinstance(value, list):
        for item in value:
            reasons.extend(_failure_reasons(item, location))
    return reasons


def classify_response(tool: str, payload: dict[str, Any], *, allow_empty: bool = False) -> dict[str, Any]:
    """Require content by default; only explicit no-output execution may be empty.

    An execution success acknowledgement with empty stdout is nonempty content.
    Empty objects (e.g. {"objects": []}) are valid inspection data. A bare empty
    response is rejected unless allow_empty=True for execute_blender_code.
    Known error signals always win over any acknowledgement or empty policy.
    """
    reasons = []
    if not isinstance(payload, dict):
        return {'status': 'FAILED', 'reasons': ['MCP payload must be an object']}
    if payload.get('isError') is True:
        reasons.append('MCP isError is true')
    if allow_empty and tool != 'execute_blender_code':
        reasons.append('empty content is allowed only for explicitly no-output execution')
    content = payload.get('content')
    if not isinstance(content, list):
        reasons.append('missing or invalid tool content')
        content = []
    usable = False
    for block in content:
        if not isinstance(block, dict):
            reasons.append('invalid content block')
        elif block.get('type') == 'image':
            if block.get('data') or block.get('local_image'):
                usable = True
            else:
                reasons.append('image content lacks data or saved-image reference')
        elif block.get('type') == 'text':
            text = block.get('text')
            if not isinstance(text, str):
                reasons.append('invalid text content')
            elif text.strip():
                usable = True
                reasons.extend(_failure_reasons(text, 'content'))
            elif not allow_empty:
                reasons.append('empty text content')
        else:
            reasons.append('unrecognized content block requires review')
    structured = payload.get('structuredContent')
    if structured is not None:
        if not isinstance(structured, dict):
            reasons.append('invalid structuredContent')
        else:
            reasons.extend(_failure_reasons(structured, 'structuredContent'))
    if not usable and not allow_empty:
        reasons.append('no usable recognized content')
    if tool == 'get_viewport_screenshot' and not any(
            isinstance(b, dict) and b.get('type') == 'image' and (b.get('data') or b.get('local_image'))
            for b in content):
        reasons.append('screenshot tool returned no image')
    return {'status': 'FAILED' if reasons else 'PASSED', 'reasons': reasons,
            'empty_content_policy': 'allowed_execution_only' if allow_empty else 'required_nonempty',
            'scope': 'MCP call result only; not production, physics or perception acceptance'}
