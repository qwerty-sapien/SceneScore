"""Synthetic wire fixtures, not headset/participant validation."""
from array import array
import math

import pytest

from modules.muse.acquisition.muse_protocol import (
    ATHENA_UUID, CHANNEL_NAMES, CONTROL_UUID, EEG_CHARACTERISTICS, SERVICE_UUID,
    FrameAssembler, PacketIndexUnwrapper, ProtocolError, decode_eeg_packet,
    encode_command, parse_packet_index, validate_classic_profile,
)
from modules.muse.acquisition.ble_clock import BLEClock


# Independent hand-written hex vector: two 12-bit values in each three bytes.
# [0,4095,1,4094,2048,2047,0x123,0xabc,256,512,1024,3072].
WIRE_VECTOR = bytes.fromhex("1234 000fff 001ffe 8007ff 123abc 100200 400c00")
COUNTS = (0, 4095, 1, 4094, 2048, 2047, 0x123, 0xabc, 256, 512, 1024, 3072)


def packet(index, value=2048):
    # A constant fixture deliberately avoids reusing decoder packing logic.
    word = f"{value:03x}" * 12
    return index.to_bytes(2, "big") + bytes.fromhex(word)


def complete(assembler, index, now, channels=CHANNEL_NAMES):
    frames = []
    for channel in channels:
        frames.extend(assembler.add(channel, packet(index, 2048 + CHANNEL_NAMES.index(channel)), now))
    return frames


@pytest.mark.parametrize("command,expected", [
    ("h", b"\x02h\n"), ("s", b"\x02s\n"), ("p21", b"\x04p21\n"),
    ("d", b"\x02d\n"), ("k", b"\x02k\n"),
])
def test_commands(command, expected):
    assert encode_command(command) == expected


@pytest.mark.parametrize("command", ["", "p20", "d\nh", "é", "x" * 300, None, []])
def test_rejects_unapproved_commands(command):
    with pytest.raises(ProtocolError, match="^unsupported_muse_command$"):
        encode_command(command)


def test_profile_case_insensitive_and_extra_characteristics_allowed():
    validate_classic_profile([SERVICE_UUID.upper()],
                             [CONTROL_UUID, *EEG_CHARACTERISTICS.values(), "extra"])


@pytest.mark.parametrize("services,chars", [
    ([], [CONTROL_UUID, *EEG_CHARACTERISTICS.values()]),
    ([SERVICE_UUID], list(EEG_CHARACTERISTICS.values())),
    ([SERVICE_UUID], [CONTROL_UUID, *list(EEG_CHARACTERISTICS.values())[:3]]),
])
def test_profile_requires_exact_service_and_four_channels(services, chars):
    with pytest.raises(ProtocolError, match="^gatt_profile_mismatch$"):
        validate_classic_profile(services, chars)


def test_athena_marker_always_rejected_before_classic_writes():
    with pytest.raises(ProtocolError, match="^unsupported_athena_profile$"):
        validate_classic_profile([SERVICE_UUID],
                                 [CONTROL_UUID, *EEG_CHARACTERISTICS.values(), ATHENA_UUID.upper()])


def test_known_vector_unpacking_index_and_microvolt_scale():
    decoded = decode_eeg_packet(WIRE_VECTOR)
    assert decoded.packet_index == 0x1234
    assert decoded.samples_uv == tuple((count - 2048) * 125 / 256 for count in COUNTS)
    assert decoded.samples_uv[:2] == (-1000.0, 999.51171875)
    assert decoded.samples_uv[4:6] == (0.0, -0.48828125)


@pytest.mark.parametrize("length", [0, 1, 2, 18, 19, 21, 1000])
def test_rejects_malformed_lengths(length):
    with pytest.raises(ProtocolError, match="^malformed_eeg_packet$"):
        decode_eeg_packet(bytes(length))


def test_byte_views_and_non_byte_length_validation():
    assert decode_eeg_packet(memoryview(WIRE_VECTOR)) == decode_eeg_packet(bytearray(WIRE_VECTOR))
    with pytest.raises(ProtocolError, match="^malformed_eeg_packet$"):
        decode_eeg_packet(memoryview(array("H", [0] * 20)))
    with pytest.raises(ProtocolError, match="^malformed_eeg_packet$"):
        parse_packet_index([0] * 20)


def test_rollover_unwrap_and_reordered_previous_cycle():
    unwrap = PacketIndexUnwrapper()
    assert [unwrap.unwrap(index) for index in (65534, 65535, 0, 65535, 1)] == [
        65534, 65535, 65536, 65535, 65537]
    unwrap.reset()
    assert unwrap.unwrap(0) == 0


@pytest.mark.parametrize("first,second", [(100, 0), (100, 9000), (100, 99 - 8), (5, 32773)])
def test_ambiguous_counter_movements_require_reconnect(first, second):
    unwrap = PacketIndexUnwrapper()
    unwrap.unwrap(first)
    with pytest.raises(ProtocolError, match="^packet_clock_reset$"):
        unwrap.unwrap(second)


def test_four_channel_assembly_preserves_order_and_sample_times():
    assembler = FrameAssembler()
    assert assembler.add("AF8", packet(10, 2050), 1.0) == []
    assert assembler.add("TP10", packet(10, 2051), 1.001) == []
    assert assembler.add("TP9", packet(10, 2048), 1.002) == []
    frames = assembler.add("AF7", packet(10, 2049), 1.003)
    assert len(frames) == 1
    frame = frames[0]
    assert frame.samples_uv == ((0, 125 / 256, 250 / 256, 375 / 256),) * 12
    assert frame.first_sample_index == 120
    assert frame.device_times_s == tuple(value / 256 for value in range(120, 132))
    assert frame.first_receipt_s == 1
    assert frame.received_monotonic_s == 1.003
    assert frame.dropped_samples == 0
    assert assembler.buffered_frames == 0


def test_never_combines_different_indexes_and_reorders_complete_future_frame():
    assembler = FrameAssembler()
    assert assembler.add("TP9", packet(10), 1) == []
    assert complete(assembler, 11, 1.02) == []
    frames = []
    for name in CHANNEL_NAMES[1:]:
        frames += assembler.add(name, packet(10), 1.04)
    assert [frame.unwrapped_index for frame in frames] == [10, 11]
    assert [frame.dropped_samples for frame in frames] == [0, 0]


def test_reordered_first_receipts_preserve_source_order_and_do_not_reset_clock():
    assembler = FrameAssembler(frame_timeout_s=.25)
    clock = BLEClock()
    first = complete(assembler, 0, 1)[0]
    clock.observe(first.device_times_s[-1], first.first_receipt_s)
    assert complete(assembler, 2, 1.05) == []
    assembler.add("TP9", packet(1), 1.1)
    # Future index 2 has been buffered >.25s. Index 1 still has until 1.35s.
    assert assembler.expire(1.31) == []
    frames = []
    for name in CHANNEL_NAMES[1:]:
        frames += assembler.add(name, packet(1), 1.32)
    assert [frame.unwrapped_index for frame in frames] == [1, 2]
    assert [frame.first_receipt_s for frame in frames] == [1.1, 1.05]
    assert [frame.dropped_samples for frame in frames] == [0, 0]
    for frame in frames:
        clock.observe(frame.device_times_s[-1], frame.first_receipt_s)
    assert clock.diagnostics(1.32)["reordered_receipt_count"] == 1
    assert clock.probe(1.32)["uncertainty_s"] > .025


def test_late_future_channel_cannot_complete_expired_frame_behind_live_partial():
    assembler = FrameAssembler(frame_timeout_s=.25)
    complete(assembler, 0, 1)
    for name in CHANNEL_NAMES[:3]:
        assembler.add(name, packet(2), 1.05)
    assembler.add("TP9", packet(1), 1.1)
    assert assembler.add("TP10", packet(2), 1.31) == []
    frames = []
    for name in CHANNEL_NAMES[1:]:
        frames += assembler.add(name, packet(1), 1.32)
    assert [frame.unwrapped_index for frame in frames] == [1]
    assert assembler.dropped_samples == 12
    assert assembler.buffered_frames == 0
    assert complete(assembler, 3, 1.33)[0].dropped_samples == 12


def test_already_emitted_out_of_order_rejected():
    assembler = FrameAssembler()
    complete(assembler, 5, 1)
    with pytest.raises(ProtocolError, match="^out_of_order_packet$"):
        assembler.add("TP9", packet(5), 1.01)
    assert assembler.rejected_packets == 1
    assert assembler.buffered_frames == 0


def test_complete_repeated_old_frame_is_ambiguous_short_reset_requires_epoch():
    assembler = FrameAssembler()
    complete(assembler, 0, 1)
    complete(assembler, 1, 1.05)
    for name in CHANNEL_NAMES[:3]:
        with pytest.raises(ProtocolError, match="^out_of_order_packet$"):
            assembler.add(name, packet(0), 1.1)
    with pytest.raises(ProtocolError, match="^packet_clock_reset$"):
        assembler.add(CHANNEL_NAMES[-1], packet(0), 1.1)


def test_conflicting_duplicate_does_not_discard_ready_frames():
    assembler = FrameAssembler(frame_timeout_s=.2)
    assembler.add("TP9", packet(0), 1)
    complete(assembler, 1, 1.05)
    assembler.add("TP9", packet(2), 1.1)
    with pytest.raises(ProtocolError, match="^malformed_eeg_packet$"):
        assembler.add("TP9", packet(2, 2000), 1.21)
    frames = assembler.expire(1.21)
    assert [frame.unwrapped_index for frame in frames] == [1]
    assert frames[0].dropped_samples == 12


def test_partial_timeout_is_charged_exactly_once_then_reported_next_frame():
    assembler = FrameAssembler(frame_timeout_s=.2)
    assembler.add("TP9", packet(50), 1)
    assert assembler.expire(1.21) == []
    assert assembler.buffered_frames == 0
    assert assembler.dropped_samples == 12
    assert assembler.expire(1.3) == []
    assert assembler.dropped_samples == 12
    frames = complete(assembler, 51, 1.31)
    assert frames[0].dropped_samples == 12
    assert complete(assembler, 52, 1.36)[0].dropped_samples == 0


def test_late_last_channel_cannot_resurrect_expired_frame():
    assembler = FrameAssembler(frame_timeout_s=.2)
    for name in CHANNEL_NAMES[:3]:
        assembler.add(name, packet(5), 1)
    assert assembler.add("TP10", packet(5), 1.21) == []
    assert assembler.dropped_samples == 12
    assert assembler.buffered_frames == 0


def test_entire_missing_indexes_and_partial_frame_gap_accounting():
    assembler = FrameAssembler(frame_timeout_s=.2)
    complete(assembler, 0, 1)
    assembler.add("TP9", packet(2), 1.1)
    complete(assembler, 4, 1.2)
    frames = assembler.expire(1.41)
    assert [frame.unwrapped_index for frame in frames] == [4]
    assert frames[0].dropped_samples == 36
    assert assembler.dropped_frames == 3
    assert assembler.dropped_samples == 36


def test_buffer_bounds_hold_under_absent_channels_and_large_gap():
    assembler = FrameAssembler(max_buffered_frames=3, frame_timeout_s=2)
    for index in range(50):
        assembler.add("AF7", packet(index), 1 + index / 256)
        assert assembler.buffered_frames <= 3
    assembler.add("AF7", packet(1000), 1.3)
    assert assembler.buffered_frames <= 3
    assert assembler.dropped_samples >= 47 * 12


def test_rollover_frames_keep_epoch_and_no_drop():
    assembler = FrameAssembler()
    frames = complete(assembler, 65535, 1) + complete(assembler, 0, 1.05)
    assert [frame.unwrapped_index for frame in frames] == [65535, 65536]
    assert frames[1].device_times_s[0] - frames[0].device_times_s[-1] == 1 / 256
    assert frames[1].dropped_samples == 0


def test_duplicate_never_creates_extra_frame_conflicting_duplicate_rejected():
    assembler = FrameAssembler()
    assembler.add("AF7", packet(0), 1)
    assert assembler.add("AF7", packet(0), 1.01) == []
    assert assembler.duplicate_packets == 1
    with pytest.raises(ProtocolError, match="^malformed_eeg_packet$"):
        assembler.add("AF7", packet(0, 2000), 1.02)
    assert assembler.malformed_packets == 1


def test_reset_clears_frames_counters_and_packet_clock():
    assembler = FrameAssembler()
    assembler.add("TP9", packet(300), 1)
    assembler.expire(1.3)
    assembler.reset()
    assert assembler.dropped_samples == assembler.buffered_frames == 0
    assert complete(assembler, 0, .1)[0].unwrapped_index == 0


@pytest.mark.parametrize("timestamp", [-1, math.inf, math.nan])
def test_invalid_receipt_clock_rejected(timestamp):
    with pytest.raises(ProtocolError, match="^packet_clock_reset$"):
        FrameAssembler().add("TP9", packet(0), timestamp)
