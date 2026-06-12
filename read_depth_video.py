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
import base64
import json
import os
import shutil
import subprocess

import numpy as np

# 256x3 uint8 Turbo colormap LUT (matplotlib's `turbo`), embedded so this
# script needs no matplotlib at runtime. Must match the converter's LUT exactly
# so the inversion in `depth_video_to_norm` lands on the right indices.
_TURBO_B64 = (
    "MBI7MhVDMxhKNBtRNR5YNiFfNyRmOCdtOSpzOi15Oy+APDKGPTWLPjiRPzuXPz6cQECiQUOn"
    "QUasQkmxQku1Q066RFG/RFTDRFbHRVnLRVzPRV7TRmHWRmTaRmbdRmngRmvjR27mR3HpR3Pr"
    "R3buR3jwR3vyRn30RoD2RoL4RoX6Rof7RYr8RYz9RI/+Q5H+QpT/QZb/QJn/Ppv+PZ7+O6D9"
    "OqP8OKX7N6j6Nav4M633Ma/1L7L0LrTyLLfwKrnuKLzrJ77pJcDnI8PkIsXiIMffH8ndHsva"
    "HM3YG9DVGtLSGtTQGdXNGNfKGNnIGNvFGN3CGN7AGOC9GeK7GeO5GuS2HOa0HeeyH+mvIOqs"
    "IuuqJeynJ+6kKu+hLPCeL/GbMvKYNfOUOPSRPPWOP/aKQ/eHRviESviATvl9Uvp6Vfp2Wftz"
    "XfxvYfxsZf1paf1mbf5icf5fdf5cef5Zff9WgP9ThP9RiP9Oi/9Lj/9Jkv9Hlv5Emf5CnP5A"
    "n/0/of09pPw8p/w6qfs5rPs4r/o3sfk2tPg2t/c1ufY1vPU0vvQ0wfM0w/E0xvA0yO80y+00"
    "zew00Oo00uk11Oc11+U12eQ22+I23eA339834d0349s45dk459c56dU569M57NE67s867806"
    "8cs68sk69Mc69cU69sM698E6+L45+bw5+ro5+7g4+7Y3/LM2/LE2/a41/aw0/qkz/qcy/qQx"
    "/qEw/p4v/pst/pks/pYr/pMq/pAp/Y0n/Yom/Icl/IQj+4Ei+34h+nsf+Xge+XUd+HIc928a"
    "9mwZ9WkY9GYX82MV8mAU8V0T8FsS71gR7VUQ7FMP61AO6k4N6EsM50kM5UcL5EUK4kMK4UEJ"
    "3z8I3T0I3DsH2jkH2DcG1jUG1DMF0jEF0C8Fzi0EzCsEyioEyCgDxSYDwyUDwSMCviECvCAC"
    "uR4Ctx0CtBsBshoBrxgBrBcBqRYBpxQBpBMBoRIBnhABmw8BmA4BlQ0BkgsBjgoBiwkCiAgC"
    "hQcCgQYCfgUCegQD"
)
TURBO = np.frombuffer(base64.b64decode(_TURBO_B64), np.uint8).reshape(256, 3)

_ffmpeg = None


def ffmpeg_bin():
    """Resolve the ffmpeg executable, falling back to the pip static binary.

    Cached per process so we only pay the lookup once.
    """
    global _ffmpeg
    if _ffmpeg is None:
        if shutil.which("ffmpeg") is None:
            try:
                import static_ffmpeg
                static_ffmpeg.add_paths()
            except ImportError:
                pass
        _ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    return _ffmpeg


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
