"""Cut EPIC-KITCHENS segments into the clips the V-JEPA 2 EK100 probe expects.

Mirrors the repo's validation pipeline (evals/action_anticipation_frozen/
epickitchens.py + dataloader.py) with OpenCV instead of decord, which has no
Apple Silicon build: 32 frames, one every int(video_fps / 8) frames, ending
1 s before an anticipation point; resize the short side to 292, centre-crop
256, scale to [0, 1] and normalise with ImageNet mean/std.

Two anticipation points:
  strict  the clip ends 1 s before the action starts (the EK100 challenge rule)
  repo    the clip ends 1 s before the action *stops*, which is what the repo's
          validation does (val_anticipation_point defaults to [0, 0], so
          af = stop_frame - 1 s); the clip can then show the action itself
"""
from __future__ import annotations

import cv2
import numpy as np
import torch

FRAMES, FPS, CROP, ANTICIPATION_SEC = 32, 8, 256, 1.0
SHORT_SIDE = int(CROP * 256 / 224)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def frame_indices(start_frame: int, stop_frame: int, video_fps: float, protocol: str) -> np.ndarray:
    step = int(video_fps / FPS)
    end = (start_frame if protocol == "strict" else stop_frame) - int(ANTICIPATION_SEC * video_fps)
    idx = np.arange(end - FRAMES * step, end, step).astype(np.int64)
    idx[idx < 0] = 0  # too close to the start of the video: repeat the first frame, as the repo does
    return idx


def read_frames(cap: cv2.VideoCapture, indices: np.ndarray) -> np.ndarray:
    """RGB frames at the given indices, read in one forward pass (seeking an MP4 is slow)."""
    want = sorted(set(indices.tolist()))
    got: dict[int, np.ndarray] = {}
    cap.set(cv2.CAP_PROP_POS_FRAMES, want[0])
    pos = want[0]
    for i in want:
        while pos < i:
            cap.grab()
            pos += 1
        ok, bgr = cap.read()
        pos += 1
        if not ok:
            raise IOError(f"could not read frame {i}")
        got[i] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.stack([got[i] for i in indices.tolist()])


def to_tensor(frames: np.ndarray) -> torch.Tensor:
    """[T, H, W, 3] uint8 -> [3, T, 256, 256] normalised float."""
    h, w = frames.shape[1:3]
    scale = SHORT_SIDE / min(h, w)
    size = (round(w * scale), round(h * scale))
    out = []
    for f in frames:
        f = cv2.resize(f, size, interpolation=cv2.INTER_LINEAR)
        y, x = (f.shape[0] - CROP) // 2, (f.shape[1] - CROP) // 2
        out.append(f[y:y + CROP, x:x + CROP])
    x = (np.stack(out).astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(x).permute(3, 0, 1, 2).contiguous()


def keyframe_jpeg(frames: np.ndarray, width: int = 320) -> bytes:
    """The last frame the model saw, small, for the results page."""
    f = frames[-1]
    f = cv2.resize(f, (width, round(f.shape[0] * width / f.shape[1])), interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()
