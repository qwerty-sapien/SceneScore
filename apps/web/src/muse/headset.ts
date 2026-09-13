import type {BridgeStatus,MuseMode,MuseOperation} from './types';
import {visibleMode} from './state';

const errors:Record<string,string>={
 bluetooth_powered_off:'Bluetooth is off on this computer.',
 bluetooth_permission_denied:'Bluetooth permission is unavailable for the local Python process.',
 bluetooth_unavailable:'Bluetooth is unavailable to the local companion. Check this computer’s Bluetooth adapter and Python Bluetooth access, then rescan.',
 scan_timeout:'Muse scan timed out. Check that the headset is powered on, then rescan.',
 muse_not_found:'No advertising Muse headset found.',
 scan_result_expired:'This discovery has expired. Rescan before connecting.',
 unknown_device_id:'This headset is not in the companion’s current scan. Rescan and select the headset again.',
 invalid_device_id:'The headset selection is invalid. Select a headset from a fresh Muse scan.',
 already_connected:'A Muse headset is already connected.',
 connect_timeout:'Muse connection timed out. Rescan and try connecting again.',
 gatt_profile_mismatch:'This headset does not expose the required classic Muse EEG profile.',
 unsupported_athena_profile:'This Athena Muse profile is not supported by the classic Muse connection.',
 stream_configuration_failed:'Muse connected, but EEG configuration failed. Rescan to try again.',
 stream_start_timeout:'Muse connected, but valid EEG samples did not arrive in time.',
 malformed_eeg_packet:'Muse sent an invalid EEG packet. Detector disarmed; waiting for a continuous valid stream.',
 packet_clock_reset:'The Muse sample clock restarted. Detector disarmed; reconnect required.',
 unexpected_disconnect_reconnect_required:'Muse disconnected. Detector disarmed; reconnect required.',
 stream_timeout_reconnect_required:'Muse stopped sending EEG samples. Detector disarmed; reconnect required.',
 disconnect_failed:'Muse disconnect could not be confirmed. Check the local companion before reconnecting.',
 muse_operation_in_progress:'A headset operation is already in progress.',
 operation_in_progress:'A headset operation is already in progress. Wait for it to finish before trying again.',
 companion_session_changed:'The companion session changed. Reconnect the companion before continuing.',
 companion_session_required:'Connect the local companion before scanning for Muse.',
 invalid_muse_scan_response:'The companion returned an invalid discovery result. Rescan to try again.',
 invalid_muse_device_id:'Select a headset from a fresh Muse scan.',
};
export function museError(error:unknown):string {
 const code=error instanceof Error?error.message:typeof error==='string'?error:'';
 if(errors[code])return errors[code];
 if(error instanceof Error&&error.name==='TimeoutError')return 'The companion request timed out. Check its current headset state before retrying.';
 return 'The headset request failed. Check the local companion, then rescan. Keyboard and simulation remain available.';
}
export function sameStream(a:BridgeStatus|null,b:BridgeStatus|null):boolean {
 return !!a&&!!b&&a.device_epoch===b.device_epoch&&a.host_epoch===b.host_epoch&&a.config_hash===b.config_hash&&a.mode===b.mode;
}
export function detectorEligible(status:BridgeStatus|null):boolean {
 return !!status&&status.source_available&&status.connected&&status.quality==='good'&&status.warmup_ready&&!status.reconnect_required&&(status.mode!=='LIVE_MUSE'||status.hardware_verified);
}
export function conductingPresentation(requested:MuseMode,status:BridgeStatus|null,operation:MuseOperation|null){
 const active=requested==='LIVE_MUSE'&&(headsetBusy(status,operation)||status?.reconnect_required)?'KEYBOARD':visibleMode(requested,status);
 const title=requested==='LIVE_MUSE'?'LIVE_MUSE':active;
 const subtitle=requested==='LIVE_MUSE'&&active!=='LIVE_MUSE'?'Live Muse selected · detector disarmed':active==='LIVE_MUSE'?'Live stream · armed':active==='REAL_REPLAY'?'Recorded signal · replay':active==='SYNTHETIC_TEST'?'Simulated · no headset evidence':'Keyboard · no headset required';
 return {active,title,subtitle};
}
export function headsetBusy(status:BridgeStatus|null,operation:MuseOperation|null):boolean {
 return !!operation||!!status?.bluetooth_state&&['scanning','connecting','gatt_verifying','configuring','subscribing','starting_stream','disconnecting'].includes(status.bluetooth_state);
}
export function headsetProgress(status:BridgeStatus|null,operation:MuseOperation|null):string {
 if(status?.reconnect_required)return museError(status.last_error??'unexpected_disconnect_reconnect_required');
 if(status?.last_error)return museError(status.last_error);
 const stage=status?.bluetooth_state;
 if(operation==='scan'&&(stage==='idle'||stage==='disconnected'||!stage))return 'Scanning…';
 if(operation==='connect'&&(stage==='idle'||stage==='disconnected'||!stage))return 'Connecting…';
 if(operation==='disconnect')return 'Disconnecting…';
 const messages:Record<string,string>={idle:'Ready to scan for Muse.',scanning:'Scanning…',connecting:'Connecting…',gatt_verifying:'Verifying Muse GATT…',configuring:'Configuring Muse EEG…',subscribing:'Subscribing to EEG…',starting_stream:'Starting EEG…',disconnecting:'Disconnecting…',disconnected:'Muse disconnected. Scan to connect again.',error:'Muse connection needs attention.'};
 if(status?.connected&&status.hardware_verified)return 'Streaming · '+status.sample_count.toLocaleString('en-US')+' samples';
 return messages[stage??'idle']??'Waiting for valid EEG samples.';
}
export function qualityExplanation(status:BridgeStatus|null):string {
 if(status?.quality==='good')return 'Calibrated numeric checks passed · contact impedance is not measured.';
 if(status?.reason.includes('profile_missing'))return 'Quality profile missing · detector remains disarmed. Supply a calibrated profile to the local companion.';
 if(status?.quality==='bad')return 'Signal checks failed · detector remains disarmed. Music and keyboard controls remain available.';
 return 'Signal quality is unverified · detector remains disarmed. A valid calibrated quality profile is required.';
}
