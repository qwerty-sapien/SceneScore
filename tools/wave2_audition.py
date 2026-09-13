"""Bounded explicit Phase 2 candidate render; no approval or transport activation."""
import argparse
from pathlib import Path
import json
import os

from modules.arranger.core import Context, TransitionPreview, baseline, compile_preview, encoded, tick_seconds
from modules.blender.summary import compact_summary
from modules.blender.selection import selected_bundle
from modules.blender.production.playback import create_playback_window
from modules.music.catalog import get_composition, get_groove
from modules.music.render import RenderBudget, render_events

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--out',type=Path,default=ROOT/'artifacts/arranger/evaluated-hero-audition')
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'artifacts/arranger'):
        raise ValueError('audition_output_outside_artifacts')
    if out.exists():
        raise FileExistsError('audition_output_exists: preserve prior evidence')
    out.mkdir(parents=True)
    bundle,selection = selected_bundle('hero',args.selection)
    summary = compact_summary(bundle)
    composition = get_composition('tilted_blue_v1')
    groove = get_groove(composition['groove_id'])
    # Full local states give the causal request policy coverage absent in compact samples.
    states = [json.loads(line) for line in (bundle/'object_states.jsonl').read_text().splitlines()]
    roles=None
    if (bundle/'object_roles.json').is_file():
        roles=json.loads((bundle/'object_roles.json').read_text())
        geometry=json.loads((bundle/'geometry.json').read_text())
        roles['validated_contact_ids']=[e['id'] for e in geometry['event_details'] if e.get('validated') and e.get('foley_eligible')]
        states=[s for s in states if s['object_id'] in roles['scored_object_ids']]
    ctx = Context(summary['scene'], states, summary['events'], composition, groove,role_supplement=roles)
    plan = baseline(ctx)
    events = compile_preview(ctx, plan)
    default_request = TransitionPreview(plan, ctx).request('horizontal-protagonist', ctx.scene['duration_s']*.4, source_mode='keyboard')
    # Explicit reviewer-visible alternative focus: descending top tower, not the horizontal projectile.
    plan['motion_policy']['focus_object_id'] = '10_projectile_tower:tower-2'
    preview = TransitionPreview(plan, ctx)
    request = preview.request('tower-descent-audition', ctx.scene['duration_s']*.6, source_mode='keyboard')
    (out/'input.json').write_bytes(encoded({'context': {'scene':ctx.scene,'states':states,'interactions':ctx.interactions,
                                                       'composition':composition,'groove':groove}}))
    (out/'plan.json').write_bytes(encoded(plan))
    (out/'baseline-events.json').write_bytes(encoded(events))
    (out/'transition-events.json').write_bytes(encoded(preview.events))
    (out/'foley-events.json').write_bytes(encoded([e for e in events if e['event_type']=='foley']))
    duration = tick_seconds(composition, composition['length_ticks'])
    window,window_hash=create_playback_window(encoded(events),ctx.scene['duration_s'])
    (out/'playback-window.json').write_bytes(encoded(window))
    measurements = {}
    print(json.dumps({'pid':os.getpid(),'outputs':str(out),'render_budget_s_each':120}), flush=True)
    for name, source in [('baseline',events),('transition',preview.events)]:
        pitched_brush = [e for e in source if e['event_type']!='foley']
        measurements[name] = render_events(pitched_brush, out/(name+'.wav'), duration_s=duration,
                                           sample_rate=48000, output_root=ROOT/'artifacts/arranger',
                                           budget=RenderBudget(max_bytes=128*1024*1024))
    report = {'status':'TECHNICAL_CANDIDATES_RENDERED','human_approval':'NOT_CREATED',
              'audition_status':'AUDITION_PENDING','audio_scope':'MUSIC_AND_BRUSHES_ONLY_FOLEY_EXCLUDED',
              'full_av_transport':'NOT_ASSESSED', 'selection':selection,
              'playback_window_sha256':window_hash,'render_scope':'full original editable-score audition; window projection is separate','process_id':os.getpid(),
              'scene_hash':ctx.scene_hash,'composition_hash':ctx.composition_hash,'scene_records':len(states),
              'default_horizontal_focus_result':default_request,'explicit_tower_focus_preview':request,
              'event_count':len(events),'render_measurements':measurements}
    (out/'audition-report.json').write_bytes(encoded(report))
    print(json.dumps({'status':report['status'],'audition_status':report['audition_status']}), flush=True)


if __name__ == '__main__':
    main()
