/** Phase 1 fake-clock contract helper, not an audio engine. */
import type { ClockMapping, ControlAction } from '../contracts/generated';
import { validate } from '../contracts/validate';
export function mapClock(m: ClockMapping, seconds: number, epoch: string): number {
  validate(m);
  if(epoch!==m.source_epoch || seconds<m.valid_from_s || seconds>m.valid_until_s) throw Error('stale_clock');
  return m.destination_anchor_s+(seconds-m.source_anchor_s)*m.rate;
}
export function classifyClosedSequence(count: number, profile='double_modulate_mvp', closed=true): string {
  if(!closed) return 'pending';
  if(!['double_modulate_mvp','multi_count_expression_experiment'].includes(profile)) throw Error('unknown_profile');
  return count===2 ? 'request_modulation' : count===3 && profile==='multi_count_expression_experiment' ? 'toggle_approved_expression_preset' : 'none';
}
export class FakeScheduler {
  seen=new Set<string>(); sequences=new Set<string>();
  queue: {action_id: string; time_s: number; lanes: ControlAction['after']}[]=[];
  constructor(public epoch='fixture-1', public now=2) {}
  reset(epoch: string, now: number) { this.epoch=epoch; this.now=now; this.queue=[]; }
  submit(a: ControlAction, request: number, expiry: number, barSeconds=2.5, horizon=.1): string {
    validate(a);
    if(a.status==='suppressed') return a.reason!;
    if(a.request.epoch!==this.epoch) return 'stale_epoch';
    if(this.seen.has(a.id)||this.sequences.has(a.sequence_id)) return 'duplicate';
    if(request>this.now||expiry<=this.now) return 'future_or_expired';
    if(barSeconds<=0||horizon<0) throw Error('scheduler_parameters');
    const boundary=Math.ceil((this.now+horizon)/barSeconds)*barSeconds;
    if(boundary>=expiry) return 'expired_before_boundary';
    this.seen.add(a.id); this.sequences.add(a.sequence_id);
    this.queue.push({action_id:a.id,time_s:boundary,lanes:{...a.after}});
    return 'queued';
  }
}
