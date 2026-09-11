/* Generated from contracts/0.1/schema.json. Do not edit. */

export type SceneScoreRecord =
  | AcquisitionMetadata
  | EEGChunk
  | BlinkCandidate
  | GestureEvent
  | ControlAction
  | SceneManifest
  | ObjectState
  | InteractionEvent
  | CompositionSpec
  | BrushGroove
  | ScoreEvent
  | AudioAssetManifest
  | ArrangementPlan
  | Approval
  | ClockMapping
  | RunManifest
  | EvaluationReport
  | CapabilityRequest;

export interface AcquisitionMetadata {
  kind: "AcquisitionMetadata";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  session_id: string;
  device_model: string;
  transport: string;
  sample_rate_hz: number;
  /**
   * @minItems 1
   */
  channels: [Channel, ...Channel[]];
  clock_epoch: string;
  hardware_verified: boolean;
  raw_storage: "local_only";
}
export interface Provenance {
  source_mode: "real_device" | "replay" | "synthetic" | "keyboard" | "manual_plan" | "cached_gpt" | "live_gpt";
  creator: string;
  tool_version: string;
  config_hash: string;
  /**
   * @minItems 0
   */
  input_hashes: string[];
  seed: number | null;
}
export interface Channel {
  name: string;
  unit: "uV" | "V";
  enabled: boolean;
}
export interface EEGChunk {
  kind: "EEGChunk";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  session_id: string;
  sequence: number;
  sample_start_index: number;
  sample_rate_hz: number;
  /**
   * @minItems 1
   */
  channels: [Channel, ...Channel[]];
  /**
   * @minItems 0
   */
  device_times_s: number[];
  host_receipt: Time;
  /**
   * @minItems 0
   */
  samples: [number, ...number[]][];
  dropped_samples_before: number;
  quality: Quality;
  imu: {
    unit: "m/s2" | "rad/s";
    /**
     * @minItems 0
     */
    samples: [number, number, number][];
  } | null;
  device_epoch: string;
}
export interface Time {
  seconds: number;
  clock: "device" | "host_monotonic" | "scene" | "transport" | "audio";
  epoch: string;
}
export interface Quality {
  state: "good" | "bad" | "dropout" | "unverified";
  reason: string | null;
}
export interface BlinkCandidate {
  kind: "BlinkCandidate";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  session_id: string;
  start: Time;
  end: Time;
  model_version: string;
  score: number;
  score_type: "uncalibrated" | "calibrated_probability";
  quality: Quality;
}
export interface GestureEvent {
  kind: "GestureEvent";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  session_id: string;
  /**
   * @minItems 1
   */
  candidate_ids: [string, ...string[]];
  gesture_count: number;
  start: Time;
  end: Time;
  final_blink: Time;
  decision: Time;
  closure_delay_s: number;
  grammar_hash: string;
  status: "accepted" | "rejected";
  reason: string | null;
  quality: Quality;
}
export interface ControlAction {
  kind: "ControlAction";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  gesture_id: string;
  sequence_id: string;
  gesture_count: number;
  profile: "double_modulate_mvp" | "multi_count_expression_experiment";
  action: "request_modulation" | "toggle_approved_expression_preset" | "none";
  request: Time;
  expires: Time;
  boundary: "next_approved_bar_or_phrase" | "next_approved_bar" | "none";
  signed_semitones: -2 | 0 | 2;
  scene_policy_id: string | null;
  approved_plan_hash: string | null;
  status: "queued" | "executed" | "suppressed";
  reason: string | null;
  quality: Quality;
  before: LaneState;
  after: LaneState;
}
export interface LaneState {
  master_gain_db: number;
  articulation: string;
  expression_preset: string;
}
export interface SceneManifest {
  kind: "SceneManifest";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  source_hash: string;
  render_hash: string | null;
  generator_version: string;
  fps: number;
  fps_base: number;
  start_frame: number;
  duration_s: number;
  units: "metres";
  up_axis: "Z";
  handedness: "right";
  quaternion_order: "xyzw";
  matrix_layout: "row_major_column_vectors";
  camera: {
    id: string;
    transform: Transform;
  };
  /**
   * @minItems 1
   */
  objects: [
    {
      object_id: string;
      sonic_identity_id: string;
    },
    ...{
      object_id: string;
      sonic_identity_id: string;
    }[]
  ];
}
export interface Transform {
  /**
   * @minItems 3
   * @maxItems 3
   */
  position_m: [number, number, number];
  /**
   * @minItems 4
   * @maxItems 4
   */
  quaternion_xyzw: [number, number, number, number];
  /**
   * @minItems 16
   * @maxItems 16
   */
  matrix_row_major: [
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number,
    number
  ];
}
export interface ObjectState {
  kind: "ObjectState";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  scene_id: string;
  object_id: string;
  scene_time_s: number;
  frame: number;
  transform: Transform;
  velocity_m_s: [number, number, number] | null;
  acceleration_m_s2: [number, number, number] | null;
  derivative_method: string;
  /**
   * @minItems 3
   * @maxItems 3
   */
  bounds_min_m: [number, number, number];
  /**
   * @minItems 3
   * @maxItems 3
   */
  bounds_max_m: [number, number, number];
  surface_area_m2: number;
  volume_m3: number | null;
  unavailable_reason: string | null;
}
export interface InteractionEvent {
  kind: "InteractionEvent";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  scene_id: string;
  /**
   * @minItems 2
   * @maxItems 2
   */
  pair: [string, string];
  pair_id: string;
  loop_instance: number;
  event_type:
    "approach" | "separation" | "near_miss" | "collision" | "contact_onset" | "contact_sustain" | "contact_release";
  onset_s: number;
  duration_s: number;
  centre_distance_m: number;
  surface_gap_m: number;
  relative_normal_speed_m_s: number;
  relative_tangential_speed_m_s: number;
  method: "analytic" | "scripted" | "baked" | "heuristic";
  physical_impact: boolean;
  impulse_ns: number | null;
  uncertainty_m: number;
}
export interface CompositionSpec {
  kind: "CompositionSpec";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  catalog_version: number;
  title: string;
  ppq: number;
  /**
   * @minItems 2
   * @maxItems 2
   */
  meter: [number, number];
  length_ticks: number;
  /**
   * @minItems 1
   */
  tempo_map: [Tempo, ...Tempo[]];
  /**
   * @minItems 1
   */
  key_map: [Key, ...Key[]];
  /**
   * @minItems 1
   */
  harmony: [Chord, ...Chord[]];
  /**
   * @minItems 1
   */
  notes: [Note, ...Note[]];
  pitch_convention: "C4=MIDI60";
  timing: "unswung_quarter_note_ticks";
  swing_ratio: number;
  groove_id: string;
  groove_version: number;
  /**
   * @minItems 1
   */
  creative_traits: [string, ...string[]];
  audition_status: "AUDITION_PENDING" | "approved" | "changes_requested";
}
export interface Tempo {
  tick: number;
  bpm: number;
}
export interface Key {
  tick: number;
  tonic_pc: number;
  mode: string;
}
export interface Chord {
  start_tick: number;
  duration_ticks: number;
  root_pc: number;
  /**
   * @minItems 1
   */
  intervals_semitones: [number, ...number[]];
  quality: string;
}
export interface Note {
  start_tick: number;
  duration_ticks: number;
  midi_pitch: number;
  velocity: number;
  articulation: string;
  swingable: boolean;
}
export interface BrushGroove {
  kind: "BrushGroove";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  catalog_version: number;
  ppq: number;
  length_ticks: number;
  /**
   * @minItems 2
   * @maxItems 2
   */
  meter: [number, number];
  pitched: false;
  /**
   * @minItems 1
   */
  events: [
    {
      start_tick: number;
      duration_ticks: number;
      technique: "sweep" | "tap" | "accented_swish" | "chick";
      velocity: number;
      hand: "left" | "right" | "foot";
      swingable: boolean;
      sample_id: string | null;
    },
    ...{
      start_tick: number;
      duration_ticks: number;
      technique: "sweep" | "tap" | "accented_swish" | "chick";
      velocity: number;
      hand: "left" | "right" | "foot";
      swingable: boolean;
      sample_id: string | null;
    }[]
  ];
  max_humanize_ms: number;
  max_velocity_delta: number;
}
export interface ScoreEvent {
  kind: "ScoreEvent";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  plan_id: string;
  object_id: string | null;
  lane_id: string;
  event_type: "note" | "brush" | "foley";
  instrument_id: string;
  start_tick: number | null;
  duration_ticks: number | null;
  resolved_time_s: number;
  duration_s: number;
  scene_time_s: number | null;
  midi_pitch: number | null;
  velocity: number;
  dynamics_db: number;
  articulation: string;
  phrasing: string;
  ornament: string | null;
  timbre_id: string;
  swing_applied: boolean;
  swing_application_count: 0 | 1;
}
export interface AudioAssetManifest {
  kind: "AudioAssetManifest";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  asset_hash: string;
  stem_id: string;
  sample_rate_hz: number;
  channels: number;
  duration_s: number;
  timeline_origin_s: number;
  source: string;
  license: string;
  renderer_version: string;
  pitched: boolean;
  sample_peak: number | null;
  measurement_status: "measured" | "not_run";
}
export interface ArrangementPlan {
  kind: "ArrangementPlan";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  scene_hash: string;
  composition_hash: string;
  /**
   * @minItems 1
   */
  palette_ids: [string, ...string[]];
  groove_id: string;
  groove_version: number;
  /**
   * @minItems 1
   */
  motif_owners: [
    {
      object_id: string;
      motif_id: string;
    },
    ...{
      object_id: string;
      motif_id: string;
    }[]
  ];
  /**
   * @minItems 1
   */
  mappings: [
    {
      feature: "approach" | "separation" | "surface_gap" | "collision" | "vertical_motion";
      lane: "key" | "chord" | "register" | "dynamics" | "articulation" | "phrasing" | "ornament" | "timbre";
      input_min: number;
      input_max: number;
      output_min: number;
      output_max: number;
    },
    ...{
      feature: "approach" | "separation" | "surface_gap" | "collision" | "vertical_motion";
      lane: "key" | "chord" | "register" | "dynamics" | "articulation" | "phrasing" | "ornament" | "timbre";
      input_min: number;
      input_max: number;
      output_min: number;
      output_max: number;
    }[]
  ];
  /**
   * @minItems 1
   */
  transitions: [Transition, ...Transition[]];
  register_min: number;
  register_max: number;
  motion_policy: {
    id: string;
    focus_object_id: string;
    axis: "Z";
    lookback_s: number;
    deadband_m_s: number;
    stationary_action: "none";
  };
  /**
   * @minItems 0
   */
  uncertainties: string[];
  review_status: "draft" | "pending" | "approved" | "rejected";
}
export interface Transition {
  from_pc: number;
  to_pc: number;
  signed_semitones: -2 | 2;
  mode: string;
}
export interface Approval {
  kind: "Approval";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  plan_id: string;
  approved_payload_sha256: string;
  /**
   * @minItems 1
   */
  input_hashes: [string, ...string[]];
  reviewer: string;
  reviewed_at_utc: string;
  decision: "approved" | "rejected";
  audition_status: "AUDITION_PENDING" | "approved" | "changes_requested";
}
export interface ClockMapping {
  kind: "ClockMapping";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  source_clock: "device" | "host_monotonic" | "scene" | "transport" | "audio";
  destination_clock: "device" | "host_monotonic" | "scene" | "transport" | "audio";
  source_epoch: string;
  destination_epoch: string;
  source_anchor_s: number;
  destination_anchor_s: number;
  rate: number;
  uncertainty_s: number;
  valid_from_s: number;
  valid_until_s: number;
}
export interface RunManifest {
  kind: "RunManifest";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  code_hash: string;
  config_hash: string;
  /**
   * @minItems 0
   */
  data_hashes: string[];
  schema_hash: string;
  model_hash: string | null;
  split: Split;
  /**
   * @minItems 1
   */
  commands: [string, ...string[]];
  runtime: {
    python: string | null;
    node: string | null;
    host_profile_id: string;
  };
  /**
   * @minItems 1
   */
  results: [CheckResult, ...CheckResult[]];
}
export interface Split {
  /**
   * @minItems 0
   */
  train_sessions: string[];
  /**
   * @minItems 0
   */
  development_sessions: string[];
  /**
   * @minItems 0
   */
  final_sessions: string[];
}
export interface CheckResult {
  test_id: string;
  status: "passed" | "failed" | "not_run";
  /**
   * @minItems 0
   */
  evidence_paths: string[];
  reason: string | null;
}
export interface EvaluationReport {
  kind: "EvaluationReport";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  run_id: string;
  data_mode: "synthetic" | "real_device" | "replay";
  release_status:
    | "PIPELINE_TESTED_ONLY"
    | "REAL_DATA_EXPLORATORY"
    | "SUPERVISED_DEMO_READY"
    | "TARGET_STATISTICALLY_SUPPORTED"
    | "NOT_READY";
  metrics: {
    tp: number | null;
    fn: number | null;
    fp: number | null;
    elapsed_hours: number;
    armed_hours: number;
    abstention_seconds: number;
    refractory_seconds: number;
  };
  targets_status: "targets_not_measurements";
  interval_method: string | null;
  /**
   * @minItems 0
   */
  assumptions: string[];
  /**
   * @minItems 1
   */
  results: [CheckResult, ...CheckResult[]];
}
export interface CapabilityRequest {
  kind: "CapabilityRequest";
  schema_version: "0.1";
  id: string;
  provenance: Provenance;
  capability_id: string;
  input: {
    [k: string]: unknown;
  };
  output_path: string;
  timeout_s: number;
  max_cost_usd: number;
  max_concurrency: 1;
}
