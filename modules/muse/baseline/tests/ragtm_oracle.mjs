// Test oracle: verbatim RAGTM processing statements inside a minimal synthetic harness.
// MIT (c) 2026 AETHER by RAiD. See ../RAGTM-LICENSE.txt.
import fs from 'node:fs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const selected=input.channels.filter(x=>/^(af|fp|f)/i.test(x));
const channels=selected.length?selected:input.channels.slice(0,2);
const blinkConfig={selectedChannelSet:new Set(channels),requiredChannels:Math.min(2,channels.length),selectedChannels:channels,
  warmupSamples:Math.round(input.rate),minDeviationUv:7,minAmplitudeUv:50,zScoreThreshold:4,baselineAlpha:.02,cooldownMs:250};
const blinkStatsRef={current:{}},blinkWarmupSamplesRef={current:0},lastBlinkAtMsRef={current:-Infinity};
const results=[];
for(const row of input.rows){
  const sampleTimestampMs=row.time;
  let blinkCandidateChannels=0,detectedBlinks=0,latestBlinkAtMs=null;
  for(const chName of input.channels){
    const filteredUv=row.values[chName];
          if (blinkConfig.selectedChannelSet.has(chName)) {
            const absFilteredUv = Math.abs(filteredUv);
            const existingStats = blinkStatsRef.current[chName];

            if (existingStats) {
              const dynamicDeviation = Math.max(
                existingStats.deviationUv,
                blinkConfig.minDeviationUv,
              );
              const zScore =
                (absFilteredUv - existingStats.meanAbsUv) / dynamicDeviation;

              if (
                absFilteredUv >= blinkConfig.minAmplitudeUv &&
                zScore >= blinkConfig.zScoreThreshold
              ) {
                blinkCandidateChannels += 1;
              }

              const meanDelta = absFilteredUv - existingStats.meanAbsUv;
              const deviationDelta = Math.abs(meanDelta) - existingStats.deviationUv;
              existingStats.meanAbsUv += blinkConfig.baselineAlpha * meanDelta;
              existingStats.deviationUv +=
                blinkConfig.baselineAlpha * deviationDelta;
            } else {
              blinkStatsRef.current[chName] = {
                meanAbsUv: absFilteredUv,
                deviationUv: blinkConfig.minDeviationUv,
              };
            }
          }
  }
        blinkWarmupSamplesRef.current += 1;
        const hasWarmupData =
          blinkWarmupSamplesRef.current >= blinkConfig.warmupSamples;
        const cooldownElapsed =
          sampleTimestampMs - lastBlinkAtMsRef.current >= blinkConfig.cooldownMs;
        const canDetectBlink =
          blinkConfig.requiredChannels > 0 &&
          blinkConfig.selectedChannels.length > 0;
        if (
          canDetectBlink &&
          hasWarmupData &&
          cooldownElapsed &&
          blinkCandidateChannels >= blinkConfig.requiredChannels
        ) {
          detectedBlinks += 1;
          latestBlinkAtMs = sampleTimestampMs;
          lastBlinkAtMsRef.current = sampleTimestampMs;
        }

  results.push(detectedBlinks>0);
}
process.stdout.write(JSON.stringify(results));
