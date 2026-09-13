# Media provenance

The original-DRAFT.mp4 is an unchanged copy of the user upload. Its SHA-256 is in baseline_metrics.json. The three excerpts are silent, lossy re-encodings of source intervals; they are review conveniences, not byte-identical substreams. No temporal interpolation or cadence conversion was requested. All excerpts decode at native 8 fps and 320x180.

Commands, using local source/destination paths appropriate to this pack:

```sh
ffmpeg -v error -nostdin -y -ss 12 -i original-DRAFT.mp4 -t 5 -an -c:v libx264 -crf 18 -pix_fmt yuv420p clips/12-17s-contact-freeze.mp4
ffmpeg -v error -nostdin -y -ss 18 -i original-DRAFT.mp4 -t 6 -an -c:v libx264 -crf 18 -pix_fmt yuv420p clips/18-24s-block-overlap.mp4
ffmpeg -v error -nostdin -y -ss 24 -i original-DRAFT.mp4 -t 6 -an -c:v libx264 -crf 18 -pix_fmt yuv420p clips/24-30s-unsupported-ending.mp4
```

The contact sheet was constructed from decoded video frames at 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28 and 29.875 seconds. Frames were resized from 320x180 to 480x270 and arranged in a four-column grid with time labels. It supplies sampled visual evidence, not full-motion review.
