"""Bounded C.mp4 frame analysis; extract first, then explicitly analyze that run."""
import base64
import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIDEO = ROOT.parent / 'C.mp4'
BASE = pathlib.Path(__file__).parent

if len(sys.argv) == 1:
    out = BASE / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir()
    command = [shutil.which('ffmpeg'), '-hide_banner', '-nostdin', '-threads', '2',
               '-i', str(VIDEO), '-map', '0:v:0', '-an', '-vf',
               'select=not(mod(n\\,3)),scale=768:-2,showinfo', '-vsync', '0',
               '-frames:v', '80', '-threads', '2', '-q:v', '3', str(out / 'frame-%03d.jpg')]
    job = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = job.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        job.kill()
        stdout, stderr = job.communicate()
        raise RuntimeError('Extraction timed out; child killed and reaped')
    log = stderr.decode(errors='replace')
    (out / 'ffmpeg.log').write_text(log)
    frames = sorted(out.glob('frame-*.jpg'))
    timestamps = [float(x) for x in re.findall(r'\bn:\s*\d+\s+pts:\s*-?\d+\s+pts_time:([\d.eE+-]+)', log)]
    manifest = {'video':str(VIDEO),'video_sha256':hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
                'command':command,'pid':job.pid,'exit_code':job.returncode,
                'sampling':'Every third decoded frame from 30 fps video; actual timestamps from FFmpeg showinfo',
                'audio_analyzed':False,'frames':[
                    {'file':p.name,'timestamp_s':t,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p,t in zip(frames,timestamps)]}
    assert job.returncode == 0 and 1 <= len(frames) < 80 and len(frames) == len(timestamps)
    (out / 'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'directory':str(out),'frames':len(frames),'first_s':timestamps[0],
                      'last_s':timestamps[-1],'extraction_exit':job.returncode}))
    raise SystemExit()

out = pathlib.Path(sys.argv[1]).resolve()
assert out.parent == BASE.resolve()
manifest = json.loads((out / 'manifest.json').read_text())
assert hashlib.sha256(VIDEO.read_bytes()).hexdigest() == manifest['video_sha256']
key = ''
for line in (ROOT / '.env.local').read_text(encoding='utf-8-sig').splitlines():
    name, sep, value = line.strip().partition('=')
    if sep and name == 'OPENAI_API_KEY':
        key = value.strip().strip('"').strip("'")
assert key.startswith('sk-'), 'Missing API key; no call made'
assert not (out / 'result.json').exists(), 'Existing run cannot be silently overwritten or retried'
prompt = '''Analyze this chronological sequence of video frames sampled at 10 fps.
Each supplied timestamp is actual video presentation time in seconds, not a frame
number. Use only visual evidence. No audio or geometry data is available.
Identify persistent objects and separately assess all seven scene-event classes:
approach = pair gap decreases; near_miss = approach then separation with visible
positive clearance and no contact; separation = pair gap increases; contact =
apparent first touch; sustained_contact = apparent touch persists; contact_release
= apparent touch ends; rebound = object direction reverses following touch.
Track which object actually moves; relative separation does not prove either
object reversed direction. Distinguish camera motion, rotation, and translation.
Do not force absent events. 2D overlap does not prove physical 3D contact. Label
ambiguous contact uncertain and carry uncertainty into contact release/rebound.
Name pairs with stable object IDs, not a whole scene as one object. Include clear
object interactions relevant to scoring. Group repetitive cycles concisely and
report up to 20 event instances total, prioritizing clear events.
Return JSON with summary, objects (id and visual description), assessments (an
object keyed by approach, near_miss, separation, contact, sustained_contact,
contact_release, rebound; each has status observed/uncertain/not_observed,
intervals with start_s, end_s, object_ids, evidence_timestamps_s and explanation;
and reason), and limitations. Event intervals must be supported by supplied
timestamps; instant event onset should be bracketed between adjacent samples.
Distinguish interval duration from onset uncertainty in explanations. Avoid
timing precision finer than 0.1 seconds. Output is editable proposals only, not
human approval, physics certification, or a request to execute music.'''
content = [{'type':'input_text','text':prompt}]
for frame in manifest['frames']:
    raw = (out / frame['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == frame['sha256']
    content.extend([{'type':'input_text','text':f"Video timestamp: {frame['timestamp_s']} seconds"},
                    {'type':'input_image','detail':'high',
                     'image_url':'data:image/jpeg;base64,'+base64.b64encode(raw).decode()}])
body = {'model':'gpt-4.1-mini','store':False,'max_output_tokens':4000,
        'text':{'format':{'type':'json_object'}},'input':[{'role':'user','content':content}]}
record = {'source_mode':'live_api','video':str(VIDEO),'video_sha256':manifest['video_sha256'],
          'frame_count':len(manifest['frames']),'sampling_fps':10,'image_size':'768x432',
          'detail':'high','prompt':prompt,'requested_model':body['model'],
          'max_output_tokens':4000,'attempts':1,'approval':None,'audio_analyzed':False,
          'utc':dt.datetime.now(dt.timezone.utc).isoformat()}
request = urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),
    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
start = time.monotonic()
try:
    with urllib.request.urlopen(request,timeout=60) as response:
        result = json.loads(response.read(1048576))
        text = '\n'.join(c.get('text','') for o in result.get('output',[]) for c in o.get('content',[]) if c.get('type') == 'output_text')
        record.update(http_status=response.status,request_id=response.headers.get('x-request-id'),
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
(out / 'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ('prompt','text')},indent=2))
print('Evidence:',out / 'result.json')
