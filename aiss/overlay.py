"""On-screen display (HUD) drawn onto each frame."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from aiss.detector import BBox

FONT = cv2.FONT_HERSHEY_DUPLEX
WHITE, RED, CYAN, BLUE = (255, 255, 255), (0, 0, 255), (255, 255, 86), (122, 63, 24)


def _text(img, text, org, color=WHITE, scale=0.5):
    cv2.putText(img, text, org, FONT, scale, color, 1, cv2.LINE_AA)


def draw_banner(img: np.ndarray) -> None:
    _text(img, "A I S S |", (20, 20))
    _text(img, "O N", (100, 20), RED)


def draw_live(img: np.ndarray, camera: str, now: Optional[datetime] = None) -> None:
    now = now or datetime.now()
    h = img.shape[0]
    draw_banner(img)
    _text(img, now.strftime("%d %B %Y"), (20, h - 35))
    cv2.rectangle(img, (170, h - 50), (255, h - 30), BLUE, -1)
    _text(img, now.strftime("%H:%M:%S"), (175, h - 35))
    _text(img, camera, (20, h - 15))


def draw_intrusion(
    img: np.ndarray,
    bbox: Optional[BBox],
    active: bool,
    patience_left: float,
    now: Optional[datetime] = None,
) -> None:
    now = now or datetime.now()
    h = img.shape[0]
    if bbox:
        x, y, w, bh = bbox
        cv2.rectangle(img, (x, y), (x + w, y + bh), CYAN, 2)
        cv2.putText(img, "Activity Detected", (x, max(12, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1, cv2.LINE_AA)
    draw_banner(img)
    _text(img, f"Room Activity: {active}", (150, 20), CYAN)
    _text(img, f"Patience: {patience_left:.2f}", (20, h - 38), RED)
    _text(img, now.strftime("%A, %H:%M:%S  %d %B %Y"), (20, h - 20))
