import Ajv2020 from 'ajv/dist/2020.js';
import schema from '../../contracts/0.1/schema.json';
import type { SceneScoreRecord } from './generated';
const validateSchema = new Ajv2020({ allErrors: true, strict: false }).compile(schema);
export function validate(data: unknown): SceneScoreRecord {
  const finite = (v: unknown): void => {
    if (typeof v === 'number' && !Number.isFinite(v)) throw Error('non_finite');
    if (v && typeof v === 'object') Object.values(v).forEach(finite);
  };
  finite(data);
  if (!validateSchema(data)) throw Error('schema_invalid');
  const d = data as SceneScoreRecord;
  semantic(d);
  return d;
}
const requireThat = (condition: boolean, reason: string) => { if (!condition) throw Error(reason); };
const unique = (v: unknown[]) => new Set(v).size === v.length;
const increasing = (v: number[]) => v.every((x,i) => i === 0 || v[i-1] < x);
export function semantic(d: SceneScoreRecord): void {
  const req = requireThat;
  const times = (ts: {clock: string; epoch: string; seconds: number}[]) => {
    req(new Set(ts.map(t => `${t.clock}:${t.epoch}`)).size === 1, 'mixed_clock_or_epoch');
    req(ts.every((t,i) => i === 0 || ts[i-1].seconds <= t.seconds), 'time_reversal');
  };
  switch (d.kind) {
    case 'AcquisitionMetadata':
      req(unique(d.channels.map(c=>c.name)), 'duplicate_channels');
      req(d.provenance.source_mode !== 'real_device' || d.hardware_verified, 'unverified_real_device');
      break;
    case 'EEGChunk':
      req(unique(d.channels.map(c=>c.name)), 'duplicate_channels');
      req(d.samples.length === d.device_times_s.length, 'sample_time_length');
      req(d.samples.every(row=>row.length===d.channels.length), 'channel_dimension');
      req(increasing(d.device_times_s), 'nonmonotonic_samples');
      req(d.host_receipt.clock === 'host_monotonic', 'receipt_clock');
      req(d.imu === null || d.imu.samples.length === d.samples.length, 'imu_dimension');
      break;
    case 'BlinkCandidate':
      times([d.start,d.end]);
      req(d.score_type !== 'calibrated_probability' || (d.score >= 0 && d.score <= 1), 'probability_range');
      break;
    case 'GestureEvent':
      times([d.start,d.end,d.final_blink,d.decision]);
      req(d.candidate_ids.length === d.gesture_count, 'candidate_count');
      req(Math.abs(d.decision.seconds-d.final_blink.seconds-d.closure_delay_s)<1e-9, 'closure_delay');
      req(d.status !== 'rejected' || Boolean(d.reason), 'missing_rejection_reason');
      break;
    case 'ControlAction': {
      times([d.request,d.expires]);
      const active = d.status !== 'suppressed';
      req(active || Boolean(d.reason), 'missing_suppression_reason');
      if(active) {
        req(d.quality.state === 'good', 'quality_gate');
        req(d.approved_plan_hash !== null, 'approval_required');
        req(d.action !== 'none', 'active_noop');
      }
      if(d.action === 'request_modulation') {
        req(d.gesture_count === 2 && [-2,2].includes(d.signed_semitones), 'double_only_modulation');
        req(d.before.master_gain_db === d.after.master_gain_db && d.before.articulation === d.after.articulation && d.before.expression_preset === d.after.expression_preset, 'unrelated_lane_change');
        req(d.boundary === 'next_approved_bar_or_phrase' && d.scene_policy_id !== null, 'modulation_policy');
      }
      if(d.action === 'toggle_approved_expression_preset') {
        req(d.profile === 'multi_count_expression_experiment' && d.gesture_count === 3, 'experimental_only');
        req(Math.abs(d.after.master_gain_db-d.before.master_gain_db)<=3, 'expression_gain_bound');
      }
      if(d.profile === 'double_modulate_mvp' && d.gesture_count !== 2) req(d.action === 'none' && !active,'default_single_triple_noop');
      break;
    }
    case 'SceneManifest':
      req(unique(d.objects.map(o=>o.object_id)), 'duplicate_object');
      req(Math.abs(d.camera.transform.quaternion_xyzw.reduce((s,x)=>s+x*x,0)-1)<1e-5,'quaternion_norm');
      break;
    case 'ObjectState':
      req(Math.abs(d.transform.quaternion_xyzw.reduce((s,x)=>s+x*x,0)-1)<1e-5,'quaternion_norm');
      req(d.bounds_min_m.every((v,i)=>v<=d.bounds_max_m[i]),'bounds_inverted');
      req(![d.velocity_m_s,d.acceleration_m_s2,d.volume_m3].includes(null) || Boolean(d.unavailable_reason),'null_measure_reason');
      break;
    case 'InteractionEvent':
      req(d.pair.join('|') === [...d.pair].sort().join('|') && d.pair_id === d.pair.join('|'), 'pair_identity');
      req(!d.physical_impact || (d.method !== 'heuristic' && ['collision','contact_onset'].includes(d.event_type)), 'unsupported_impact');
      if(d.event_type === 'near_miss') req(d.surface_gap_m > d.uncertainty_m && !d.physical_impact,'unproven_near_miss');
      break;
    case 'CompositionSpec': {
      req(d.notes.every(n=>n.start_tick+n.duration_ticks<=d.length_ticks),'event_outside_form');
      req(d.length_ticks % (d.ppq*4*d.meter[0]/d.meter[1])===0,'partial_bar');
      for(const map of [d.tempo_map,d.key_map]) {
        const ticks = map.map(t=>t.tick);
        req(ticks[0]===0 && increasing(ticks) && ticks[ticks.length-1]<d.length_ticks,'map_order');
      }
      let end=0;
      for(const c of d.harmony) { req(c.start_tick===end,'harmony_gap_overlap'); end+=c.duration_ticks; }
      req(end===d.length_ticks,'harmony_length');
      break;
    }
    case 'BrushGroove':
      req(d.events.every(n=>n.start_tick+n.duration_ticks<=d.length_ticks),'event_outside_form');
      req(d.length_ticks % (d.ppq*4*d.meter[0]/d.meter[1])===0,'partial_bar');
      break;
    case 'ScoreEvent':
      req(d.swing_applied === (d.swing_application_count===1),'swing_state');
      if(d.event_type==='note') req(d.midi_pitch!==null && d.start_tick!==null && d.duration_ticks!==null,'note_fields');
      else req(d.midi_pitch===null,'unpitched_transposition');
      if(d.event_type==='foley') req(d.scene_time_s!==null && d.resolved_time_s===d.scene_time_s && d.start_tick===null && !d.swing_applied,'foley_scene_time');
      break;
    case 'ArrangementPlan':
      req(d.register_min<=d.register_max,'register_bounds');
      d.transitions.forEach(t=>req(((t.from_pc+t.signed_semitones)%12+12)%12===t.to_pc,'signed_transition'));
      d.mappings.forEach(m=>req(m.input_min<m.input_max && m.output_min<=m.output_max,'mapping_bounds'));
      req(unique(d.motif_owners.map(m=>m.object_id)),'motif_owner_conflict');
      break;
    case 'ClockMapping': req(d.valid_from_s<d.valid_until_s,'clock_validity'); break;
    case 'RunManifest':
      req(unique(Object.values(d.split).flat()),'split_leakage');
      d.results.forEach(r=>req(r.status!=='passed'||r.evidence_paths.length>0,'passed_without_evidence'));
      break;
    case 'EvaluationReport':
      req(d.metrics.armed_hours<=d.metrics.elapsed_hours,'exposure_range');
      if(d.data_mode==='synthetic') req(['PIPELINE_TESTED_ONLY','NOT_READY'].includes(d.release_status),'synthetic_performance_claim');
      d.results.forEach(r=>req(r.status!=='passed'||r.evidence_paths.length>0,'passed_without_evidence'));
      break;
  }
}

export function validateBundle(input: unknown[]): SceneScoreRecord[] {
  const records=input.map(validate);
  const byId=new Map(records.map(r=>[r.id,r]));
  requireThat(byId.size===records.length,'duplicate_record_id');
  for(const r of records) {
    if(r.kind==='ObjectState'||r.kind==='InteractionEvent') {
      const scene=byId.get(r.scene_id);
      if(scene?.kind!=='SceneManifest') throw Error('unknown_reference');
      const ids=new Set(scene.objects.map(o=>o.object_id));
      const refs=r.kind==='ObjectState'?[r.object_id]:r.pair;
      requireThat(refs.every(id=>ids.has(id)),'unknown_object');
    }
    if(r.kind==='CompositionSpec'||r.kind==='ArrangementPlan') {
      const groove=byId.get(r.groove_id);
      if(groove?.kind!=='BrushGroove') throw Error('unknown_reference');
      requireThat(groove.catalog_version===r.groove_version,'groove_version');
    }
    if(r.kind==='ScoreEvent') {
      const plan=byId.get(r.plan_id);
      if(plan?.kind!=='ArrangementPlan') throw Error('unknown_reference');
      requireThat(plan.palette_ids.includes(r.instrument_id),'unknown_instrument');
    }
  }
  return records;
}
