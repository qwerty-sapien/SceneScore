"""Pure classic Muse EEG protocol; no Bluetooth, clocks, jobs or raw-data logging.

Wire references (independent implementations, not hardware-validation evidence):
https://github.com/alexandrebarachant/muse-lsl/blob/master/muselsl/constants.py
https://github.com/alexandrebarachant/muse-lsl/blob/master/muselsl/muse.py
https://github.com/urish/muse-js/blob/master/src/lib/muse-parse.ts
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable

SERVICE_UUID = "0000fe8d-0000-1000-8000-00805f9b34fb"
CONTROL_UUID = "273e0001-4c4d-454d-96be-f03bac821358"
ATHENA_UUID = "273e0013-4c4d-454d-96be-f03bac821358"
CHANNEL_NAMES = ("TP9", "AF7", "AF8", "TP10")
EEG_CHARACTERISTICS = {
    name: f"273e{number:04x}-4c4d-454d-96be-f03bac821358"
    for name, number in zip(CHANNEL_NAMES, (3, 4, 5, 6))
}
SAMPLE_RATE_HZ = 256
SAMPLES_PER_PACKET = 12
EEG_PACKET_BYTES = 20
UV_PER_COUNT = 125 / 256
SUPPORTED_COMMANDS = frozenset(("h", "s", "p21", "d", "k"))


class ProtocolError(ValueError):
    """A bounded code, never packet contents or a native exception string."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def encode_command(command: str) -> bytes:
    """Encode only the narrow transport command set, including newline length."""
    if not isinstance(command, str) or command not in SUPPORTED_COMMANDS:
        raise ProtocolError("unsupported_muse_command")
    body = command.encode("ascii")
    return bytes((len(body) + 1,)) + body + b"\n"


def validate_classic_profile(service_uuids: Iterable[str],
                             characteristic_uuids: Iterable[str]) -> None:
    """Validate supplied GATT identities before any classic control command.

    The I/O layer supplies the characteristics belonging to the Muse service.
    An Athena marker always wins, even when classic UUIDs are also present.
    """
    services = {str(uuid).lower() for uuid in service_uuids}
    characteristics = {str(uuid).lower() for uuid in characteristic_uuids}
    if ATHENA_UUID in characteristics:
        raise ProtocolError("unsupported_athena_profile")
    if (SERVICE_UUID not in services
            or not {CONTROL_UUID, *EEG_CHARACTERISTICS.values()} <= characteristics):
        raise ProtocolError("gatt_profile_mismatch")


@dataclass(frozen=True)
class EEGPacket:
    packet_index: int
    samples_uv: tuple[float, ...]


def parse_packet_index(packet: bytes | bytearray | memoryview) -> int:
    if not isinstance(packet, (bytes, bytearray, memoryview)):
        raise ProtocolError("malformed_eeg_packet")
    data = bytes(packet)
    if len(data) != EEG_PACKET_BYTES:
        raise ProtocolError("malformed_eeg_packet")
    return int.from_bytes(data[:2], "big")


def decode_eeg_packet(packet: bytes | bytearray | memoryview) -> EEGPacket:
    """Decode 16-bit big-endian index and twelve unsigned packed 12-bit values.

    Each three-byte group contains two samples. Convert the unsigned midpoint
    2048 to zero microvolts without filtering or channel subtraction.
    """
    index = parse_packet_index(packet)
    data = bytes(packet)
    samples = []
    for offset in range(2, EEG_PACKET_BYTES, 3):
        first, middle, last = data[offset:offset + 3]
        samples.extend((((first << 4) | (middle >> 4)) - 2048,
                        (((middle & 15) << 8) | last) - 2048))
    return EEGPacket(index, tuple(value * UV_PER_COUNT for value in samples))


class PacketIndexUnwrapper:
    """Nearest 16-bit unwrap with a small, explicit cross-channel reorder window.

    Backward movements outside the window and forward jumps beyond the stated
    structural bound are ambiguous with restart, so require a new stream epoch.
    A delayed old packet inside the window can be rejected by the assembler;
    counters alone cannot distinguish every short reset from delayed delivery.
    """

    def __init__(self, *, reorder_window: int = 8, max_forward_jump: int = 4096):
        if (type(reorder_window) is not int or not 0 <= reorder_window <= 128
                or type(max_forward_jump) is not int
                or not reorder_window < max_forward_jump < 32768):
            raise ValueError("invalid_packet_index_bounds")
        self.reorder_window = reorder_window
        self.max_forward_jump = max_forward_jump
        self.highest: int | None = None

    def reset(self) -> None:
        self.highest = None

    def unwrap(self, index: int) -> int:
        if type(index) is not int or not 0 <= index <= 65535:
            raise ProtocolError("malformed_eeg_packet")
        if self.highest is None:
            self.highest = index
            return index
        delta = ((index - (self.highest & 65535) + 32768) % 65536) - 32768
        if delta < -self.reorder_window or delta > self.max_forward_jump:
            raise ProtocolError("packet_clock_reset")
        logical = self.highest + delta
        if logical < 0:
            raise ProtocolError("out_of_order_packet")
        self.highest = max(self.highest, logical)
        return logical


@dataclass(frozen=True)
class EEGFrame:
    packet_index: int
    unwrapped_index: int
    samples_uv: tuple[tuple[float, ...], ...]
    first_receipt_s: float
    received_monotonic_s: float
    dropped_samples: int

    @property
    def first_sample_index(self) -> int:
        return self.unwrapped_index * SAMPLES_PER_PACKET

    @property
    def device_times_s(self) -> tuple[float, ...]:
        return tuple((self.first_sample_index + offset) / SAMPLE_RATE_HZ
                     for offset in range(SAMPLES_PER_PACKET))


@dataclass
class _PendingFrame:
    first_receipt_s: float
    last_receipt_s: float
    channels: dict[str, tuple[float, ...]] = field(default_factory=dict)


class FrameAssembler:
    """Emit strictly ordered complete four-channel frames; never impute samples.

    ``add`` and ``expire`` return zero or more frames. Call ``expire`` from the
    transport timer as well, so silent partial frames are evicted. A frame waits
    for at most ``frame_timeout_s`` from its first notification. Missing indexes
    are charged as twelve dropped samples per logical frame, not per channel.
    Dropped samples accumulate on the next returned frame for EEGChunk's existing
    discontinuity semantics. Receipt timestamps must be caller-owned monotonic.
    """

    def __init__(self, *, max_buffered_frames: int = 8,
                 frame_timeout_s: float = .25, reorder_window: int = 8):
        if (type(max_buffered_frames) is not int or not 1 <= max_buffered_frames <= 128
                or not math.isfinite(frame_timeout_s) or not .01 <= frame_timeout_s <= 2):
            raise ValueError("invalid_frame_buffer_bounds")
        self.max_buffered_frames = max_buffered_frames
        self.frame_timeout_s = frame_timeout_s
        self._unwrapper = PacketIndexUnwrapper(reorder_window=reorder_window)
        self.reset()

    def reset(self) -> None:
        self._unwrapper.reset()
        self._frames: dict[int, _PendingFrame] = {}
        self._stale_channels: dict[int, set[str]] = {}
        self._next_index: int | None = None
        self._last_receipt_s: float | None = None
        self._pending_drops = 0
        self.dropped_samples = 0
        self.dropped_frames = 0
        self.malformed_packets = 0
        self.rejected_packets = 0
        self.duplicate_packets = 0

    @property
    def buffered_frames(self) -> int:
        return len(self._frames)

    def _check_time(self, receipt_s: float) -> None:
        if (not math.isfinite(receipt_s) or receipt_s < 0
                or (self._last_receipt_s is not None and receipt_s < self._last_receipt_s)):
            raise ProtocolError("packet_clock_reset")
        self._last_receipt_s = receipt_s

    def add(self, channel_name: str, packet: bytes | bytearray | memoryview,
            receipt_s: float) -> list[EEGFrame]:
        self._check_time(receipt_s)
        try:
            if channel_name not in CHANNEL_NAMES:
                raise ProtocolError("malformed_eeg_packet")
            decoded = decode_eeg_packet(packet)
        except ProtocolError:
            self.malformed_packets += 1
            raise
        try:
            index = self._unwrapper.unwrap(decoded.packet_index)
            if self._next_index is None:
                self._next_index = index
            if index < self._next_index:
                # One delayed notification is harmless to reject. A complete
                # repeated old frame is indistinguishable from a short counter
                # restart, so require reconnect rather than silently catch up.
                stale = self._stale_channels.setdefault(index, set())
                stale.add(channel_name)
                while len(self._stale_channels) > self._unwrapper.reorder_window + 1:
                    del self._stale_channels[min(self._stale_channels)]
                if len(stale) == len(CHANNEL_NAMES):
                    raise ProtocolError("packet_clock_reset")
                raise ProtocolError("out_of_order_packet")
        except ProtocolError:
            self.rejected_packets += 1
            raise
        existing = self._frames.get(index)
        if existing is not None and channel_name in existing.channels:
            self.duplicate_packets += 1
            if existing.channels[channel_name] != decoded.samples_uv:
                self.malformed_packets += 1
                raise ProtocolError("malformed_eeg_packet")
            return self._drain(receipt_s)
        if (existing is not None and len(existing.channels) < len(CHANNEL_NAMES)
                and receipt_s - existing.first_receipt_s >= self.frame_timeout_s):
            # A future frame can already be expired while an earlier source
            # frame is still within its own deadline. It must not be completed
            # by this late channel while waiting for the earlier frame to drain.
            self.rejected_packets += 1
            return self._drain(receipt_s)
        # Expire before inserting: a late final channel cannot resurrect a frame
        # whose deadline has passed. The incoming index remains accounted as lost.
        ready = self._drain(receipt_s)
        if index < self._next_index:
            self.rejected_packets += 1
            return ready
        pending = self._frames.get(index)
        if pending is None:
            pending = self._frames[index] = _PendingFrame(receipt_s, receipt_s)
        pending.channels[channel_name] = decoded.samples_uv
        pending.last_receipt_s = receipt_s
        return ready + self._drain(receipt_s)

    def expire(self, now_s: float) -> list[EEGFrame]:
        self._check_time(now_s)
        return self._drain(now_s)

    def _drop_to(self, next_index: int) -> None:
        assert self._next_index is not None and next_index > self._next_index
        count = next_index - self._next_index
        for index in tuple(self._frames):
            if index < next_index:
                del self._frames[index]
        self._next_index = next_index
        self.dropped_frames += count
        self.dropped_samples += count * SAMPLES_PER_PACKET
        self._pending_drops += count * SAMPLES_PER_PACKET

    def _drain(self, now_s: float) -> list[EEGFrame]:
        ready = []
        while self._frames:
            assert self._next_index is not None
            pending = self._frames.get(self._next_index)
            if pending is not None and len(pending.channels) == len(CHANNEL_NAMES):
                index = self._next_index
                rows = tuple(tuple(pending.channels[name][sample] for name in CHANNEL_NAMES)
                             for sample in range(SAMPLES_PER_PACKET))
                ready.append(EEGFrame(index & 65535, index, rows, pending.first_receipt_s,
                                      pending.last_receipt_s, self._pending_drops))
                self._pending_drops = 0
                del self._frames[index]
                self._next_index += 1
                continue
            waiting_since = (pending.first_receipt_s if pending is not None else
                             min(frame.first_receipt_s for frame in self._frames.values()))
            timed_out = now_s - waiting_since >= self.frame_timeout_s
            over_bound = len(self._frames) > self.max_buffered_frames
            too_far = max(self._frames) - self._next_index >= self.max_buffered_frames
            if not (timed_out or over_bound or too_far):
                break
            # Missing entire ranges can be charged in one operation; partial
            # frames are evicted one at a time to preserve any later complete one.
            self._drop_to(self._next_index + 1 if pending is not None else min(self._frames))
        return ready
