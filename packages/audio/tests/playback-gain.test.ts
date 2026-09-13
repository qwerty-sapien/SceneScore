import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultPlaybackGain} from '../../../apps/web/src/library/playback-gain';
import {amplitude} from '../mix';

const scene_hash='9330d5e9a4cf91e1c8ea7be0cc5da7ab5c29f4a4daf3aee9a160787756386cfb';
const scores=[
 '14ed0ab3e5bac543c3a1bdf519ff25a01c2206b14015a2cf6a2528e7943ff4d1',
 '2434f906db31cbfbce05dd5e77230a9ef75720cc577a98a735479732b0a8185c',
 '06aa8d937cf05159956da130a8c6d131156e3674b721260926f0261e96e41dc6',
];

test('the three measured staircase scores start 12 dB louder',()=>{
 for(const events_sha256 of scores)assert.equal(defaultPlaybackGain({scene_hash,events_sha256}),-6);
});
test('unmeasured scenes and replacement scores retain the conservative default',()=>{
 assert.equal(defaultPlaybackGain({scene_hash:'0'.repeat(64),events_sha256:scores[0]}),-18);
 assert.equal(defaultPlaybackGain({scene_hash,events_sha256:'0'.repeat(64)}),-18);
});
test('authored sound-design gain overrides the measured scene default',()=>{
 for(const db of [-36,-24,0])assert.equal(defaultPlaybackGain({scene_hash,events_sha256:scores[0],sound_design:{default_gain_db:db}}),db);
});
test('a louder default leaves manual attenuation, mute and separate lanes intact',()=>{
 const gain_db=defaultPlaybackGain({scene_hash,events_sha256:scores[0]});
 const point={scene_s:0,gain_db,muted:false,lanes:{soundtrack:true,foley:true}};
 assert.ok(Math.abs(amplitude(point,'soundtrack')/10**(-18/20)-10**(12/20))<1e-12);
 assert.equal(amplitude({...point,muted:true},'foley'),0);
 assert.equal(amplitude({...point,lanes:{soundtrack:false,foley:true}},'soundtrack'),0);
 assert.ok(amplitude({...point,gain_db:-24},'soundtrack')<amplitude(point,'soundtrack'));
});
