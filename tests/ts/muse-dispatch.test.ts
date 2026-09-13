import test from 'node:test';
import assert from 'node:assert/strict';
import envelopeFixture from '../../modules/muse/runtime/tests/control-envelope.json';
import musicFixture from '../../packages/audio/tests/fixture.json';
import {Timeline} from '../../packages/audio/transport';
import {copy, type Bundle} from '../../packages/audio/model';
import {validate} from '../../packages/contracts/validate';
import type {ArrangementPlan, ControlAction} from '../../packages/contracts/generated';

test('Python envelope action passes frozen TypeScript contract without extra canonical fields', () => {
  assert.equal(envelopeFixture.version, 'muse-control-envelope-1');
  validate(envelopeFixture.action);
  assert.equal(envelopeFixture.timing.t3_request_s - envelopeFixture.timing.t1_decision_s, 10);
  assert.equal(envelopeFixture.timing.t4_received_s, null);
  assert.equal(envelopeFixture.timing.t5_ack_onset_s, null);
  assert.equal(envelopeFixture.timing.t6_boundary_s, null);
});

// All LIVE/REPLAY paths in this file are software fixtures, not device validation.
for (const mode of ['keyboard', 'synthetic', 'replay', 'real_device'] as const) {
  test(`${mode}: canonical adapter action uses Timeline.submit gates and one-pending limit`, () => {
    const bundle = copy(musicFixture.bundle) as unknown as Bundle;
    const plan = JSON.parse(bundle.plan_bytes) as ArrangementPlan;
    const timeline = new Timeline(bundle, plan, 'a'.repeat(64));
    const makeAction = (suffix: string): ControlAction => {
      const a = copy(envelopeFixture.action) as ControlAction;
      a.id += suffix; a.sequence_id += suffix; a.gesture_id += suffix;
      a.provenance.source_mode = mode;
      // Trusted music context binding, no detector direction calculation.
      a.scene_policy_id = plan.motion_policy.id;
      return a;
    };
    const now = envelopeFixture.action.request.seconds;
    const submit = (action: ControlAction) => timeline.submit(action, now, 1);
    assert.equal(submit(makeAction('-stopped')).reason, 'transport_not_playing');
    timeline.playing = true;
    const suppressed = makeAction('-upstream');
    suppressed.status = 'suppressed'; suppressed.reason = 'quality_gate';
    assert.equal(submit(suppressed).reason, 'quality_gate');
    const stale = makeAction('-plan'); stale.approved_plan_hash = 'b'.repeat(64);
    assert.equal(submit(stale).reason, 'stale_plan');
    const clock = makeAction('-clock'); clock.request.epoch = clock.expires.epoch = 'old-audio';
    assert.equal(submit(clock).reason, 'unmapped_or_stale_clock');
    const expired = makeAction('-expired'); expired.expires.seconds = now;
    assert.equal(submit(expired).reason, 'future_expired_or_out_of_order');
    const short = makeAction('-short'); short.expires.seconds = now + .01;
    assert.equal(submit(short).reason, 'no_feasible_boundary_before_expiry');
    const accepted = makeAction('-accepted');
    const decision = submit(accepted);
    assert.equal(decision.status, 'queued');
    assert.equal(decision.audio_received_s, now);
    assert.equal(submit(accepted).reason, 'duplicate');
    const repeatedSequence = makeAction('-renamed');
    repeatedSequence.sequence_id = accepted.sequence_id;
    assert.equal(submit(repeatedSequence).reason, 'duplicate');
    for (let i = 0; i < 32; i++) {
      assert.equal(submit(makeAction(`-flood-${i}`)).reason, 'one_pending_request_limit');
    }
    assert.equal(timeline.pending.length, 1);
    timeline.reset(1);
    assert.equal(timeline.pending.length, 0);
    assert.equal(decision.status, 'cancelled_on_transport_reset');
  });
}
