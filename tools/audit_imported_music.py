"""Independently check persisted WAVs, MIDI timing and copied video streams."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave


def digest(file):
    return hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()


def read_wav(file):
    with wave.open(str(file), 'rb') as audio:
        assert audio.getsampwidth() == 2 and audio.getnchannels() == 2
        samples = array('h', audio.readframes(audio.getnframes()))
        if sys.byteorder != 'little':
            samples.byteswap()
        return samples, audio.getnframes(), audio.getframerate()


def midi_check(file, expected_notes, expected_seconds):
    data = file.read_bytes()
    assert data[:4] == b'MThd'
    tracks = int.from_bytes(data[10:12], 'big')
    ppq = int.from_bytes(data[12:14], 'big')
    pos, note_ons, max_tick, tempo = 14, 0, 0, None
    for _ in range(tracks):
        assert data[pos:pos + 4] == b'MTrk'
        size = int.from_bytes(data[pos + 4:pos + 8], 'big')
        pos += 8
        end, tick, active = pos + size, 0, {}
        while pos < end:
            delta = 0
            while True:
                byte = data[pos]
                pos += 1
                delta = (delta << 7) | (byte & 127)
                if byte < 128:
                    break
            tick += delta
            status = data[pos]
            pos += 1
            if status == 255:
                kind, length = data[pos], data[pos + 1]
                pos += 2
                if kind == 81:
                    tempo = int.from_bytes(data[pos:pos + length], 'big')
                pos += length
            elif status & 240 == 192:
                pos += 1
            else:
                assert status & 240 in (128, 144)
                pitch, velocity = data[pos:pos + 2]
                pos += 2
                key = (status & 15, pitch)
                if status & 240 == 144 and velocity:
                    active[key] = active.get(key, 0) + 1
                    note_ons += 1
                else:
                    assert active.get(key, 0) > 0, 'MIDI note-off without note-on'
                    active[key] -= 1
            max_tick = max(max_tick, tick)
        assert not any(active.values()), 'MIDI has stuck notes'
    assert pos == len(data) and note_ons == expected_notes and tempo
    seconds = max_tick / ppq * tempo / 1_000_000
    assert abs(seconds - expected_seconds) < .002
    return {'tracks': tracks, 'notes': note_ons, 'duration_s': seconds, 'stuck_notes': 0}


def video_hash(ffmpeg, file):
    result = subprocess.run(
        [ffmpeg, '-v', 'error', '-nostdin', '-i', str(file), '-map', '0:v:0',
         '-c:v', 'copy', '-f', 'hash', '-hash', 'sha256', '-'],
        capture_output=True, text=True, check=True, timeout=90)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    parser.add_argument('ffmpeg')
    args = parser.parse_args()
    root = args.review.resolve()
    results = []
    for ident in ('A', 'B'):
        folder = root / ident
        manifest = json.loads((folder / 'manifest.json').read_text())
        assert digest(Path(manifest['input']['path'])) == manifest['input']['sha256']
        for relative, expected in manifest['source_code_sha256'].items():
            assert digest(root / 'source-used' / relative) == expected
        assert digest(folder / 'events.json') == manifest['events_sha256']
        assert digest(folder / 'composition.json') == manifest['composition_sha256']
        events = json.loads((folder / 'events.json').read_text())
        assert all(e['event_type'] != 'foley' and e['object_id'] is None for e in events)
        duration = manifest['input']['duration_s']
        assert all(0 <= e['resolved_time_s'] < e['resolved_time_s'] + e['duration_s'] <= duration + 1e-9 for e in events)
        pcm, stats = {}, {}
        for item in manifest['files']:
            file = folder / item['filename']
            assert digest(file) == item['sha256']
            samples, frames, rate = read_wav(file)
            assert frames == manifest['render']['frames'] and rate == 48000
            assert abs(frames / rate - duration) <= 1 / rate
            assert samples[0] == samples[1] == samples[-1] == samples[-2] == 0
            assert max(samples) < 32767 and min(samples) > -32768
            assert any(samples)
            pcm[item['stem']] = samples
            stats[item['stem']] = {'frames': frames, 'rate': rate, 'duration_s': frames / rate,
                                   'peak_pcm': max(abs(min(samples)), max(samples)), 'clipped': 0}
        stems = [v for k, v in pcm.items() if k != 'mix']
        maximum_difference = max(abs(total - actual) for total, actual in
                                 zip(map(sum, zip(*stems)), pcm['mix']))
        assert maximum_difference <= len(stems)
        midi = folder / f'{ident}-score.mid'
        assert digest(midi) == manifest['midi_sha256']
        midi_stats = midi_check(midi, len(events), duration)
        video = folder / manifest['video']['filename']
        assert digest(video) == manifest['video']['sha256']
        source_video_hash = video_hash(args.ffmpeg, manifest['input']['path'])
        output_video_hash = video_hash(args.ffmpeg, video)
        assert source_video_hash == output_video_hash, 'Video stream changed'
        results.append({'id': ident, 'status': 'passed', 'audio': stats, 'midi': midi_stats,
                        'max_stem_sum_error_pcm': maximum_difference,
                        'original_video_stream_unchanged': True, 'video_packet_hash': output_video_hash})
    report = {'results': results, 'browser_playback': 'not verified: no connected browser/native helper',
              'human_listening': 'pending', 'approval': None}
    output = root / 'verification.json'
    with output.open('x') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
