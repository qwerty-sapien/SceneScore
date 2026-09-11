"""Bounded explicit Phase 2 candidate render; no approval or transport activation."""
from pathlib import Path
import json
import os

from modules.arranger.core import Context, TransitionPreview, baseline, compile_preview, encoded, tick_seconds
from modules.blender.summary import compact_summary
from modules.music.catalog import get_composition, get_groove
from modules.music.render import RenderBudget, render_events

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT/'artifacts/arranger/evaluated-hero-audition'
    if out.exists():
        raise FileExistsError('audition_output_exists: preserve prior evidence')
    out.mkdir(parents=True)
    bundle = ROOT/'artifacts/blender/validated-hero/10_projectile_tower-default'
    summary = compact_summary(bundle)
    composition = get_composition('tilted_blue_v1')
    groove = get_groove(composition['groove_id'])
    # Full local states give the causal request policy coverage absent in compact samples.
    states = [json.loads(line) for line in (bundle/'object_states.jsonl').read_text().splitlines()]
    ctx = Context(summary['scene'], states, summary['events'], composition, groove)
    plan = baseline(ctx)
    events = compile_preview(ctx, plan)
    default_request = TransitionPreview(plan, ctx).request('horizontal-protagonist', 12, source_mode='keyboard')
    # Explicit reviewer-visible alternative focus: descending top tower, not the horizontal projectile.
    plan['motion_policy']['focus_object_id'] = '10_projectile_tower:tower-2'
    preview = TransitionPreview(plan, ctx)
    request = preview.request('tower-descent-audition', 18, source_mode='keyboard')
    if request['status'] != 'preview_only':
        raise ValueError('expected_unapproved_preview_transition')
    (out/'input.json').write_bytes(encoded({'context': {'scene':ctx.scene,'states':states,'interactions':ctx.interactions,
                                                       'composition':composition,'groove':groove}}))
    (out/'plan.json').write_bytes(encoded(plan))
    (out/'baseline-events.json').write_bytes(encoded(events))
    (out/'transition-events.json').write_bytes(encoded(preview.events))
    (out/'foley-events.json').write_bytes(encoded([e for e in events if e['event_type']=='foley']))
    duration = tick_seconds(composition, composition['length_ticks'])
    measurements = {}
    print(json.dumps({'pid':os.getpid(),'outputs':str(out),'render_budget_s_each':120}), flush=True)
    for name, source in [('baseline',events),('transition',preview.events)]:
        pitched_brush = [e for e in source if e['event_type']!='foley']
        measurements[name] = render_events(pitched_brush, out/(name+'.wav'), duration_s=duration,
                                           sample_rate=48000, output_root=ROOT/'artifacts/arranger',
                                           budget=RenderBudget(max_bytes=128*1024*1024))
    report = {'status':'TECHNICAL_CANDIDATES_RENDERED','human_approval':'NOT_CREATED',
              'audition_status':'AUDITION_PENDING','audio_scope':'MUSIC_AND_BRUSHES_ONLY_FOLEY_EXCLUDED',
              'full_av_transport':'NOT_IMPLEMENTED','process_id':os.getpid(),
              'scene_hash':ctx.scene_hash,'composition_hash':ctx.composition_hash,'scene_records':len(states),
              'default_horizontal_focus_result':default_request,'explicit_tower_focus_preview':request,
              'event_count':len(events),'render_measurements':measurements}
    (ROOT/'reports/phase2/arranger-audition.json').write_bytes(encoded(report))
    print(json.dumps({'status':report['status'],'audition_status':report['audition_status']}), flush=True)


if __name__ == '__main__':
    main()
