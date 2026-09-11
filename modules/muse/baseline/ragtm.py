"""Port of RAGTM frontend candidate statistics, NOT the complete RAGTM pipeline.

MIT (c) 2026 AETHER by RAiD; see RAGTM-LICENSE.txt and LINEAGE.md.
Input must already be the original filtered uV values and source timestamps.
"""
import math


class RagtmCandidatePort:
    version = "ragtm-frontend-candidate-port/1"

    def __init__(self, channel_names, sample_rate):
        frontal = [name for name in channel_names if name.lower().startswith(("af", "fp", "f"))]
        self.selected = frontal or channel_names[:2]
        self.required = min(2, len(self.selected))
        self.warmup = math.floor(sample_rate + 0.5)
        self.stats, self.count, self.last_ms = {}, 0, -math.inf

    def feed(self, filtered_uv, timestamp_ms):
        qualifying = 0
        for name in self.selected:
            amplitude = abs(filtered_uv[name])
            if not math.isfinite(amplitude) or not math.isfinite(timestamp_ms):
                raise ValueError("finite_filtered_input_required")
            if name not in self.stats:
                self.stats[name] = [amplitude, 7.0]
                continue
            mean, deviation = self.stats[name]
            score = (amplitude - mean) / max(deviation, 7.0)
            qualifying += amplitude >= 50.0 and score >= 4.0
            delta = amplitude - mean
            self.stats[name] = [mean + .02 * delta, deviation + .02 * (abs(delta) - deviation)]
        self.count += 1
        accepted = (self.required > 0 and self.count >= self.warmup
                    and timestamp_ms - self.last_ms >= 250 and qualifying >= self.required)
        if accepted:
            self.last_ms = timestamp_ms
        return accepted
