type GainInputs={scene_hash:string;events_sha256:string;sound_design?:{default_gain_db:number};piano_mix?:{default_gain_db:number}};

// Measured against these exact prepared inputs, not a title or every future staircase.
// +12 dB over the old -18 dB default: ~-37.1 dBFS RMS, peaks below -22.6 dBFS.
// This is digital playback gain, never a calibrated physical dB SPL guarantee.
const staircaseScene='9330d5e9a4cf91e1c8ea7be0cc5da7ab5c29f4a4daf3aee9a160787756386cfb';
const staircaseScores=new Set([
 '14ed0ab3e5bac543c3a1bdf519ff25a01c2206b14015a2cf6a2528e7943ff4d1',
 '2434f906db31cbfbce05dd5e77230a9ef75720cc577a98a735479732b0a8185c',
 '06aa8d937cf05159956da130a8c6d131156e3674b721260926f0261e96e41dc6',
]);

/** Call only after bundle verification. Explicit authored sound-design levels win. */
export function defaultPlaybackGain(bundle:GainInputs){
 return bundle.sound_design?.default_gain_db??bundle.piano_mix?.default_gain_db??
  (bundle.scene_hash===staircaseScene&&staircaseScores.has(bundle.events_sha256)?-6:-18);
}
