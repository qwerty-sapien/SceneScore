"""Shared causal double detector for automatic checks and production inference."""
from collections import deque
import copy

from modules.muse.baseline.causal import CausalBaseline, Config
from .checkpoints import validate_checkpoint, model_contract
from .web_model import predict_window, _digest


def acquisition_contract(metadata):
    by_name = {c["name"].upper(): c for c in metadata["channels"] if c["enabled"]}
    pair = next((p for p in (("AF7", "AF8"), ("FP1", "FP2")) if all(n in by_name for n in p)), None)
    if pair is None:
        raise ValueError("two_frontal_channels_required")
    mode = metadata["provenance"]["source_mode"]
    return {"source_mode": "real_device" if mode == "replay" else mode,
            "sample_rate_hz": metadata["sample_rate_hz"],
            "channels": [[name, by_name[name]["unit"]] for name in pair]}


class PersonalDetector(CausalBaseline):
    def __init__(self, metadata, checkpoint=None, *, exploratory_metadata=False):
        self.checkpoint = copy.deepcopy(checkpoint)
        if checkpoint is not None:
            validate_checkpoint(checkpoint)
            if model_contract(checkpoint["model"]) != acquisition_contract(metadata):
                raise ValueError("checkpoint_source_contract_mismatch")
        self.signal = deque(maxlen=int(metadata["sample_rate_hz"] * 4) + 128)
        names = [c["name"].upper() for c in metadata["channels"]]
        self.frontal_indices = [names.index(c[0]) for c in acquisition_contract(metadata)["channels"]]
        super().__init__(metadata, Config(), exploratory_metadata=exploratory_metadata)
        if checkpoint is not None:
            self.version = checkpoint["id"]

    @property
    def effective_config_hash(self):
        return _digest({"grammar": self.config.digest, "checkpoint": self.checkpoint["id"]}) if self.checkpoint else self.config.digest

    def reset(self, reason):
        self.signal.clear()
        super().reset(reason)

    def consume(self, raw):
        # Append after the base detector handles resets; retain samples of this
        # chunk only when continuity/quality checks have succeeded.
        candidates, gestures = super().consume(raw)
        if raw["quality"]["state"] == "good":
            self.signal.extend(zip(raw["device_times_s"], raw["samples"]))
        if self.checkpoint is None:
            return candidates, gestures
        for gesture in gestures:
            if gesture["status"] != "accepted":
                continue
            end = gesture["final_blink"]["seconds"]
            rows = [(t, r) for t, r in self.signal if end - 2 - 1 / self.rate <= t <= end]
            try:
                score = predict_window(self.checkpoint["model"], [t for t, _ in rows],
                                       [[r[i] for i in self.frontal_indices] for _, r in rows], self.rate)
                if score < self.checkpoint["model"]["threshold"]:
                    gesture.update(status="rejected", reason="personal_model_rejected")
            except ValueError:
                gesture.update(status="rejected", reason="personal_model_window_unavailable")
        return candidates, gestures
