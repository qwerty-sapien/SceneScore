"""Bounded LSL descriptors and explicit synthetic rehearsal. No import-time discovery."""

import math
import time


def normalized_unit(value):
    if value.strip().lower() in {"uv", "µv", "μv", "microvolt", "microvolts"}:
        return "uV"
    if value.strip().lower() in {"v", "volt", "volts"}:
        return "V"
    raise ValueError("unknown_channel_unit:" + value)


def descriptor(info):
    count, rate = info.channel_count(), info.nominal_srate()
    if not 2 <= count <= 16 or not math.isfinite(rate) or not 20 <= rate <= 1024:
        raise ValueError("unsupported_channel_count_or_nominal_rate")
    channel = info.desc().child("channels").child("channel")
    channels, original = [], []
    for _ in range(count):
        name, unit = channel.child_value("label"), channel.child_value("unit")
        if not name or len(name) > 40:
            raise ValueError("channel_label_missing")
        original.append({"name": name, "unit": unit})
        channels.append({"name": name, "unit": normalized_unit(unit)})
        channel = channel.next_sibling()
    if len({c["name"] for c in channels}) != count:
        raise ValueError("duplicate_channel_labels")
    by_name = {c["name"].lower(): i for i, c in enumerate(channels)}
    pair = next((pair for pair in (("af7", "af8"), ("fp1", "fp2")) if all(name in by_name for name in pair)), None)
    frontal = [by_name[name] for name in pair] if pair else []
    if len(frontal) != 2 or any(channels[i]["unit"] != "uV" for i in frontal):
        raise ValueError("two_identified_frontal_microvolt_channels_required")
    if not info.source_id():
        raise ValueError("unique_lsl_source_id_required")
    return {
        "id": info.source_id(),
        "name": info.name(),
        "channels": channels,
        "sample_rate_hz": rate,
        "frontal_indices": frontal,
        "original_channels": original,
    }


class LSLSource:
    def __init__(self, source_id, expected):
        import pylsl

        streams = pylsl.resolve_byprop("source_id", source_id, minimum=1, timeout=2)
        if len(streams) != 1:
            raise ValueError("exactly_one_selected_source_required")
        self.inlet = pylsl.StreamInlet(streams[0], max_buflen=2, recover=False)
        try:
            self.description = descriptor(self.inlet.info(timeout=2))
            if self.description != expected:
                raise ValueError("stream_metadata_changed_rediscover_required")
        except BaseException:
            self.inlet.close_stream()
            raise

    def pull(self):
        if hasattr(self.inlet, "was_clock_reset") and self.inlet.was_clock_reset():
            raise ValueError("lsl_clock_reset_reconnect_required")
        return self.inlet.pull_chunk(timeout=0.1, max_samples=128)

    def close(self):
        self.inlet.close_stream()


class SyntheticSource:
    """Independent 12s repeat: double3/3.3; single7; triple9/9.3/9.6; B has no input."""

    description = {
        "id": "synthetic",
        "name": "Explicit synthetic rehearsal",
        "sample_rate_hz": 256,
        "channels": [{"name": "AF7", "unit": "uV"}, {"name": "AF8", "unit": "uV"}],
        "frontal_indices": [0, 1],
        "original_channels": [],
        "schedule": "12s repeat: double3/3.3, single7, triple9/9.3/9.6; quiet elsewhere",
    }

    def __init__(self):
        self.start, self.index, self.closed = time.monotonic(), 0, False

    def pull(self):
        if self.closed:
            return [], []
        time.sleep(0.04)
        if self.closed:
            return [], []
        count = min(128, max(0, int((time.monotonic() - self.start) * 256) - self.index))
        times = [(self.index + i) / 256 for i in range(count)]
        rows = []
        for t in times:
            phase = t % 12
            pulse = sum(180 * max(0, 1 - abs(phase - c) / 0.08) for c in (3, 3.3, 7, 9, 9.3, 9.6))
            rows.append([pulse + 2 * math.sin(t * 13), 0.92 * pulse + 2 * math.cos(t * 17)])
        self.index += count
        return rows, times

    def close(self):
        self.closed = True


class Sources:
    def __init__(self):
        self.known = {}

    def discover(self):
        sources, blockers, seen, duplicates = [], [], set(), set()
        try:
            import pylsl

            advertised = pylsl.resolve_streams(wait_time=1)
            if len(advertised) > 8:
                raise ValueError("discovery_capacity_exceeded")
            for item in advertised:
                inlet = pylsl.StreamInlet(item, max_buflen=1, recover=False)
                try:
                    value = descriptor(inlet.info(timeout=1))
                    if value["id"] in seen:
                        duplicates.add(value["id"])
                        raise ValueError("duplicate_source_id")
                    seen.add(value["id"])
                    sources.append(value)
                except (ValueError, RuntimeError, OSError) as exc:
                    blockers.append(str(exc))
                finally:
                    inlet.close_stream()
        except (ImportError, ValueError, RuntimeError, OSError) as exc:
            blockers.append("LSL_unavailable:" + str(exc))
        sources = [s for s in sources if s["id"] not in duplicates]
        self.known = {s["id"]: s for s in sources}
        if not sources and not blockers:
            blockers.append("No advertised verified-descriptor LSL source found")
        return {"sources": sources, "blockers": blockers}

    def open(self, source_id):
        if source_id == "synthetic":
            return SyntheticSource()
        if source_id not in self.known:
            raise ValueError("select_a_discovered_source_first")
        return LSLSource(source_id, self.known[source_id])
