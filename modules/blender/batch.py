"""Bounded trusted-script runner; serial jobs, scoped output, no arbitrary .blend input."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from modules.blender.recipes import IDS


def bounded(command, log, timeout=600):
    """Own exact process group, record before waiting; always kill remaining owned children."""
    log=Path(log)
    log.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    result={'command':command,'timeout_s':timeout,'status':'running'}
    def interrupted(signum, frame):
        raise InterruptedError('task cancellation')
    old_handler=signal.signal(signal.SIGTERM,interrupted)
    with log.open('w') as output:
        proc=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        result.update(pid=proc.pid,pgid=proc.pid)
        evidence=log.with_suffix('.job.json')
        evidence.write_text(json.dumps(result,indent=2))
        try:
            result['returncode']=proc.wait(timeout=timeout)
            result['status']='passed' if proc.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:
            result['status']='timeout'
        except (KeyboardInterrupt, InterruptedError):
            result['status']='cancelled'
        finally:
            try:
                os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL)
                proc.wait(timeout=5)
            try:
                os.killpg(proc.pid,0)
            except ProcessLookupError:
                result['process_group_absent']=True
            else:
                os.killpg(proc.pid,signal.SIGKILL)
                result['process_group_absent']=False
            signal.signal(signal.SIGTERM,old_handler)
            result['duration_s']=time.monotonic()-started
            evidence.write_text(json.dumps(result,indent=2))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',default=os.environ.get('BLENDER_BIN'))
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--recipe',choices=IDS,action='append')
    p.add_argument('--duration',type=float)
    p.add_argument('--fps',type=int,default=12)
    p.add_argument('--timeout',type=int,default=600)
    p.add_argument('--render',action='store_true')
    p.add_argument('--variant',choices=['default','near_miss','contact'],default='default')
    a=p.parse_args()
    if not a.blender or not Path(a.blender).is_file():
        p.error('verified --blender or BLENDER_BIN required')
    if not 1<=a.timeout<=1800:
        p.error('timeout must be 1..1800 seconds')
    root=Path(__file__).resolve().parents[2]
    out=a.out.resolve()
    # Caller chooses an owned artifact scope. Refuse filesystem root/home and existing outputs.
    if out in (Path('/'),Path.home(),root):
        p.error('unsafe output root')
    result=[]
    for rid in a.recipe or IDS:
        dest=out/(rid+'-'+a.variant)
        command=[a.blender,'--background','--factory-startup','--python-exit-code','1','--threads','2',
                 '--python',str(root/'modules/blender/scenes'/f'{rid}.py'),'--','--out',str(dest),
                 '--seed','42','--fps',str(a.fps),'--variant',a.variant,'--preview']
        if a.duration:
            command+=['--duration',str(a.duration)]
        if not a.render:
            command+=['--export-only']
        r=bounded(command,out/(rid+'.log'),a.timeout)
        result.append(r)
        if r['status']!='passed' or not r['process_group_absent']:
            break
    out.mkdir(parents=True,exist_ok=True)
    (out/'batch.json').write_text(json.dumps(result,indent=2))
    return 0 if all(r['status']=='passed' and r['process_group_absent'] for r in result) else 1


if __name__=='__main__':
    raise SystemExit(main())
