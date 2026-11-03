"""Reading frames for a frame check: a 2x2 contact sheet of the last seconds, never later than the check's time."""
from __future__ import annotations

import io

import cv2
from PIL import Image


class FrameReader:
    """Frames of a video at given times, resized to px x px."""

    def __init__(self, path, px: int):
        self.cap, self.px = cv2.VideoCapture(str(path)), px

    def at(self, t: float):
        self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
        ok, bgr = self.cap.read()
        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).resize((self.px, self.px)) if ok else None


def contact_sheet(frames: FrameReader, t: float, n: int, span_s: float) -> bytes | None:
    """n frames evenly over [t - span_s, t] in a 2-wide grid, as JPEG; None if fewer than 2 frames could be read
    (e.g. past the end of a damaged video)."""
    px = frames.px
    times = [t - span_s + span_s * j / (n - 1) for j in range(n)]
    shots = [frames.at(x) for x in times]
    if sum(f is not None for f in shots) < 2:
        return None
    grid = Image.new("RGB", (2 * px, 2 * px))
    for j, f in enumerate(shots):
        if f is not None:
            grid.paste(f, (px * (j % 2), px * (j // 2)))
    buf = io.BytesIO(); grid.save(buf, "JPEG", quality=80)
    return buf.getvalue()
