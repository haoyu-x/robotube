"""Read rgb.mp4 + depth.mp4 from a converted/example RoboTube cam folder.

LIMITATION — these videos are NOT metric:
  `depth.mp4` is a Turbo-colorized visualization built with PER-FRAME min/max
  normalization (see convert_to_video_dataset.py). That scale is not stored, so
  the video CANNOT be inverted back to meters. Inverting the Turbo colormap only
  recovers a RELATIVE depth in [0, 1] per frame (0 = nearest, 1 = farthest in
  that frame; invalid/no-return pixels are black -> NaN).

  If you need true meters, read the original `{i}_depth.png` (uint16 mm) instead
  -- or re-run the converter with metric depth preserved.

Usage:
    uv run python read_depth_video.py CAM_DIR              # .../<ts>_cam_0
    uv run python read_depth_video.py CAM_DIR --frame 5
"""

import argparse
import json
import os
import shutil
import subprocess

import numpy as np

# Reuse the exact Turbo LUT + ffmpeg resolver from the converter.
from convert_to_video_dataset import TURBO, ffmpeg_bin


def _ffprobe():
    if shutil.which("ffprobe") is None:
        ffmpeg_bin()                      # registers the static binaries on PATH
    return shutil.which("ffprobe") or "ffprobe"


def read_video(path):
    """Decode an mp4 to (T, H, W, 3) uint8 RGB via ffmpeg."""
    info = json.loads(subprocess.run(
        [_ffprobe(), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", path],
        capture_output=True, text=True).stdout)["streams"][0]
    w, h = int(info["width"]), int(info["height"])
    raw = subprocess.run(
        [ffmpeg_bin(), "-v", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def depth_video_to_norm(rgb):
    """Invert Turbo: (H, W, 3) uint8 -> RELATIVE depth in [0, 1] (NaN = invalid).

    Each pixel is matched to its nearest Turbo LUT entry; index/255 is the
    per-frame-normalized depth. Black pixels are the invalid mask.
    """
    h, w, _ = rgb.shape
    flat = rgb.reshape(-1, 3).astype(np.float32)
    lut = TURBO.astype(np.float32)                  # (256, 3)
    best = np.full(flat.shape[0], np.inf, np.float32)
    idx = np.zeros(flat.shape[0], np.int32)
    for k in range(256):                            # 256 cheap vectorized passes
        d = ((flat - lut[k]) ** 2).sum(1)
        upd = d < best
        best[upd], idx[upd] = d[upd], k
    norm = (idx / 255.0).reshape(h, w)
    norm[rgb.sum(2) < 12] = np.nan                  # black = no return
    return norm


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cam_dir", help="folder containing rgb.mp4 + depth.mp4")
    ap.add_argument("--frame", type=int, default=0)
    args = ap.parse_args()

    rgb = read_video(os.path.join(args.cam_dir, "rgb.mp4"))
    depth_vid = read_video(os.path.join(args.cam_dir, "depth.mp4"))
    print(f"rgb.mp4   : {rgb.shape} uint8")
    print(f"depth.mp4 : {depth_vid.shape} uint8")

    fi = args.frame
    norm = depth_video_to_norm(depth_vid[fi])       # (H, W) relative depth [0,1]
    h, w = norm.shape
    print(f"\nframe {fi}: RELATIVE depth recovered from depth.mp4 (NOT meters)")
    print(f"  valid : {np.isfinite(norm).mean()*100:.1f}% of pixels")
    print(f"  norm  : min={np.nanmin(norm):.3f}  "
          f"median={np.nanmedian(norm):.3f}  max={np.nanmax(norm):.3f}")
    print(f"  center pixel ({h//2},{w//2}) = {norm[h//2, w//2]:.3f}  "
          f"(0=nearest, 1=farthest in this frame)")

    # `norm` is a plain numpy array of relative depth -- index norm[y, x] as usual.


if __name__ == "__main__":
    main()
