# Narrow patch for the six-hour adaptive-music milestone

The Blender revamp should otherwise continue unchanged. This patch only changes three boundaries:
1. the finalized physical scene duration is authoritative and need not remain 30 seconds;
2. the animation integration exports a clean clock plus existing/easily-derived motion and discrete-event features for downstream music heuristics;
3. soundtrack redesign and Muse/EEG work are explicitly deferred to separate DAG packs.

No physics, story, art-direction, render-quality or validation requirements were relaxed.
