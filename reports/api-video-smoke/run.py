"""One bounded, live API trial; no app integration or human approval."""
import base64
import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).parent / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT.mkdir()
VIDEO = ROOT / 'blender_revamp/evidence/original-DRAFT.mp4'
baseline = json.loads((VIDEO.parent / 'baseline_metrics.json').read_text())
digest = hashlib.sha256(VIDEO.read_bytes()).hexdigest()
assert digest == baseline['uploaded_video_sha256'], 'Source differs from documented baseline'
key = ''
for line in (ROOT / '.env.local').read_text(encoding='utf-8-sig').splitlines():
    name, sep, value = line.strip().partition('=')
    if sep and name == 'OPENAI_API_KEY':
        key = value.strip().strip('"').strip("'")
assert key.startswith('sk-'), 'API key missing; no request made'

command = [shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-threads', '2', '-i', str(VIDEO),
           '-vf', 'select=not(mod(n\\,8))+eq(n\\,239)', '-vsync', '0', '-frames:v', '31',
           '-threads', '2', '-q:v', '3', str(OUT / 'frame-%03d.jpg')]
job = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    stdout, stderr = job.communicate(timeout=45)
except subprocess.TimeoutExpired:
    job.kill()
    stdout, stderr = job.communicate()
    raise RuntimeError('Frame extraction timed out; child terminated')
(OUT / 'extraction.json').write_text(json.dumps({'command':command, 'pid':job.pid,
    'exit_code':job.returncode, 'stderr':stderr.decode(errors='replace')}, indent=2))
assert job.returncode == 0, 'Frame extraction failed'
frames = sorted(OUT.glob('frame-*.jpg'))
assert len(frames) == 31
timestamps = list(range(30)) + [29.875]
prompt = '''Analyze this chronological sequence of frames from a synthetic animation.
Frames are sampled at one-second intervals plus the last frame. Times are seconds
from video start, NOT frame numbers. Inspect only visible evidence; you have no
audio, geometry or hidden frames. Stable object names must be used throughout.
Assess all seven event types: approach (pair gap decreases), near_miss (approach
then separation with visible clearance and no contact), separation (gap increases),
contact (apparent first touch), sustained_contact (apparent touch persists),
contact_release (apparent touch ends), rebound (direction reversal following touch).
Do not force all seven to occur. 2D overlap cannot prove 3D contact; contact-related
claims should remain uncertain when depth or motion is ambiguous. Static holding
does not prove sustained physical contact. A separation alone is not a rebound.
Return a concise JSON object with summary, objects, assessments (one per event
type; status observed/uncertain/not_observed; intervals with start_s, end_s,
objects and evidence_timestamps_s; reason), and limitations. Give broad intervals
supported by samples, never sub-frame precision. No music, approval or execution.'''
content = [{'type':'input_text','text':prompt}]
manifest = []
for image, timestamp in zip(frames, timestamps):
    raw = image.read_bytes()
    manifest.append({'file':image.name,'timestamp_s':timestamp,'sha256':hashlib.sha256(raw).hexdigest()})
    content.extend([{'type':'input_text','text':f'Video timestamp: {timestamp} seconds'},
                    {'type':'input_image','detail':'low','image_url':'data:image/jpeg;base64,'+base64.b64encode(raw).decode()}])
body = {'model':'gpt-4.1-mini','store':False,'max_output_tokens':2200,
        'text':{'format':{'type':'json_object'}},'input':[{'role':'user','content':content}]}
record = {'source_mode':'live_api','media_mode':'synthetic_blender_render',
          'video':str(VIDEO.relative_to(ROOT)),'video_sha256':digest,'frames':manifest,
          'prompt':prompt,'requested_model':body['model'],'detail':'low','max_output_tokens':2200,
          'attempts':1,'approval':None,'audio_analyzed':False,
          'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
          'limitations':['Exploratory single-clip trial; not an accuracy benchmark',
                         'Baseline sidecars and review were not supplied to the model',
                         'Timestamp mapping uses verified baseline constant 8 fps and zero start']}
request = urllib.request.Request('https://api.openai.com/v1/responses',
    data=json.dumps(body).encode(), headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
start = time.monotonic()
try:
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read(1048576))
        text = '\n'.join(c.get('text','') for o in result.get('output',[]) for c in o.get('content',[]) if c.get('type') == 'output_text')
        record.update(http_status=response.status, request_id=response.headers.get('x-request-id'),
                      model=result.get('model'),status=result.get('status'),usage=result.get('usage'),text=text)
        try:
            record['analysis'] = json.loads(text)
        except ValueError:
            record['parse_status'] = 'FAILED'
except urllib.error.HTTPError as exc:
    try:
        error = json.loads(exc.read(65536)).get('error',{})
    except Exception:
        error = {}
    record.update(status='FAILED',http_status=exc.code,error_code=error.get('code'),
                  message=re.sub(r'sk-[A-Za-z0-9_-]+','[REDACTED]',str(error.get('message',''))).replace(key,'[REDACTED]'))
except Exception as exc:
    record.update(status='FAILED',error_type=type(exc).__name__)
record['elapsed_seconds'] = round(time.monotonic()-start,3)
(OUT / 'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ('frames','prompt','text')},indent=2))
print('Evidence:',OUT / 'result.json')
