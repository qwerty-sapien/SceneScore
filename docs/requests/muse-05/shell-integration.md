# Muse panel integration request

Owns only `apps/web/src/muse`, `apps/web/public/muse`, `services/bridge` and this handoff.
Mount `MusePanel` from `apps/web/src/muse/MusePanel.tsx` in the shared editing desk. Its
CSS is imported by the component and scoped under `.muse-panel`.

Props and envelope types are frozen in `apps/web/src/muse/types.ts`:

- `getMusicContext(requestAudioS?)` returns the existing transport audio epoch/time,
  exact current plan hash, policy, motion sign at request time and unchanged lanes.
- `createSimulation(context)` constructs the canonical synthetic envelope outside the UI.
- `createFromGesture(gesture,mapping,hostDispatchS,hostEpoch,context)` constructs the
  canonical action from the accepted semantic gesture and validated clock mapping.
- `onEnvelope(envelope)` calls the identical Engine/Timeline submit path and returns real
  decision fields. `t5` and `t6` are audio-clock timestamps; nullable means unavailable.
- `onKeyboardRequest()` remains permanently available and labels its source KEYBOARD.
- `transportStatus` is optional explanatory text.

The component never chooses sign, approval, gain, voicing or musical arrival. Parent owns
simulation factory, all action construction and audio scheduling. No test or model identity
may become a human approval. An automated demo must continue to carry approval:null.

Parent integration verification needs browser checks for actual audible acknowledgement
and key change, plus production build/deployment. Source/feedback state tests and bridge
source/authentication checks are included here. Check absence of the companion preserves
rendering, KEYBOARD and SYNTHETIC_TEST. Requested LIVE_MUSE may never render as active
until every runtime/hardware gate is true. Cue and prediction remain independent displays.
