# Local training API v1 — integrator seam

New owned areas: services/training/ (backend), apps/training/ (frontend),
modules/muse/training/web_model.py and tests/test_web_model.py (model).
No edits to the old semantic companion or music engine are needed.

Base URL http://127.0.0.1:8767/v1. JSON, Bearer token, no cookies. POST /session
with startup token returns {session, status}; all remaining calls use session token.
POST JSON body max 16 KiB. GET raw/review output bounded (trace max 2048 points).
Every API error is {error: human-readable-code}. Errors use non-2xx status.

GET /status => {version, connected, mode: real_device|synthetic|null, recording,
 source, channels: [{name,unit}], sample_rate_hz, measured_rate_hz, sample_count,
 last_device_s, device_epoch, quality, reason, current_session_id, sessions: SessionSummary[], model: ModelSummary|null}
SessionSummary: {id, participant_id, refit_id, role: train|development|final_test,
 source_mode, samples, duration_s, marker_count, reviewed_count, status}.
GET /sources => {sources:[{id,name,channels:[{name,unit}],sample_rate_hz}], blockers:string[]}
POST /connect {source_id, device_model, consent:true}; source_id='synthetic' is
 explicit rehearsal. Real source is selected from discovery, never guessed.
POST /disconnect {} => status. Stops any recording first.
GET /trace => {channels:[{name,unit}], times_s:number[], samples:number[][],
 device_epoch, source_mode, quality, prediction: {score,model_id,semantics}|null}
No synthetic trace on disconnected initial page.
POST /record/start {participant_id,refit_id,role,consent:true,consent_statement,
 seconds:10..600,metadata_confirmed:boolean} => status. Real recording requires
 explicit operator confirmation that the selected source and displayed descriptor
 belong to the named device, plus observed timestamp-rate consistency. This is
 operator metadata verification, not measured contact quality or model validation.
 Whole session/refit role is assigned before recording;
 deny one refit appearing in multiple roles. IDs bounded and path-safe.
POST /record/stop {} => status.
POST /marker {event:'down'|'up'|'cue',id,class_name,client_ms} => marker/status.
 class_name: double|single|triple|natural|artifact|keypress_only. B down/up has one ID,
 auto-repeat ignored. Cue creates a bounded 2-second candidate review interval.
 Store browser time, receipt time and source anchor separately with uncertainty.
 Never put browser timestamps directly into the device-clock column.
GET /review?session_id=ID => {session:SessionSummary, markers:Marker[], reviews:Review[]}
Marker: {id,class_name,start_s,end_s|null,source,review_required:true} plus timing provenance.
GET /segment?session_id=ID&start_s=N&end_s=N => trace, maximum 10 s/downsampled display.
POST /review {session_id,marker_id,start_s,end_s,class_name,certainty:'reviewed'|'uncertain',
 reviewer,notes} => review (class names above). Review only after recording stops;
 append history. Human adjusted device bounds must be within recorded data.
POST /train {} => {model:ModelSummary,report}; never trains while recording. Bounded
 fit from reviewed TRAIN sessions only, minimum 3 positive and 3 negative independent
 intervals; no overlap/duplicate augmentation. No dev/final fit. Require one source mode.
 ModelSummary: {id,status,positive_examples,negative_examples,source_mode,held_out,
 model_kind,control_authority:false}; window-level held_out may be null with reason.
GET /export?session_id=ID => local JSON raw session with metadata/chunks/markers/reviews,
 max 32 MiB. GET /model => local model JSON. User explicitly clicks Download.
POST /delete {session_id,confirmed_session_id} => status; stop before deleting;
 invalidate dependent model. Delete exact ID only.

Model module seam:
`train_model(examples)` returns {model,report}; examples each contain session_id,
participant_id,refit_id,role,source_mode,review_id,certainty:'reviewed',class_name,
times_s,samples (two frontal columns),sample_rate_hz,start_s,end_s.
`predict_window(model,times_s,samples,sample_rate_hz)` returns scalar score or raises
on invalid/short/gapped input. Fixed bounded causal 2-second window ending at interval
end; no future baseline or label/cue/key metadata in feature vector. Every reviewed
interval needs >=2 seconds of valid preceding sample coverage. Epoch continuity is
validated by backend before assembling examples. Model hashes bind exact examples.
Include deterministic fit, mode/refit/role/gap/overlap/label gates and meaningful tests.

Frontend mounts standalone apps/training/index.html and src/main.tsx; package already
provides React, TypeScript and Vite. No new dependency. Parent owns launcher/build
scripts, docs and publication. Use above exact endpoints; report any needed amendment
before divergent implementation. Display real versus synthetic and no-model states.
