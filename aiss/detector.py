"""Motion / intruder detection.

Two pieces, kept separate so the logic can be tested without a camera:

* :class:`MotionDetector` - per-frame computer vision. A Gaussian Mixture
  background model (MOG2, Zivkovic 2004/2006) segments moving foreground,
  shadows are thresholded away, the mask is dilated, and the largest contour
  above an area threshold is reported as activity.

* :class:`IntrusionMonitor` - temporal reasoning over those per-frame
  detections. An event only *starts* after ``detection_thresh`` consecutive
  positive frames (suppresses flicker / noise), and only *ends* once the
  subject has been gone for ``patience`` seconds (prevents one intrusion
  being split into many short clips and many SMS alerts).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

BBox = Tuple[int, int, int, int]  # x, y, w, h


@dataclass
class MotionDetector:
    """Background-subtraction motion detector."""

    min_area: float = 1100.0
    var_threshold: float = 50.0
    history: int = 2800
    detect_shadows: bool = True
    dilate_iterations: int = 4

    def __post_init__(self) -> None:
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows,
        )

    def mask(self, frame: np.ndarray) -> np.ndarray:
        """Return the cleaned binary foreground mask for ``frame``."""
        fg = self._bg.apply(frame)
        # MOG2 marks shadows as 127; keep only confident foreground (255).
        _, fg = cv2.threshold(fg, 250, 255, cv2.THRESH_BINARY)
        return cv2.dilate(fg, None, iterations=self.dilate_iterations)

    def detect(self, frame: np.ndarray) -> Optional[BBox]:
        """Return the bounding box of the largest moving region, or ``None``."""
        contours, _ = cv2.findContours(
            self.mask(frame), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) <= self.min_area:
            return None
        return cv2.boundingRect(largest)


class Event(Enum):
    NONE = auto()
    STARTED = auto()
    ENDED = auto()


@dataclass
class IntrusionMonitor:
    """Debounced intrusion state machine with a patience timer."""

    detection_thresh: int = 15
    patience: float = 7.0
    clock: Callable[[], float] = time.monotonic

    active: bool = field(default=False, init=False)
    _history: deque = field(init=False, repr=False)
    _gone_since: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._history = deque([False] * self.detection_thresh, maxlen=self.detection_thresh)

    @property
    def patience_left(self) -> float:
        if self._gone_since is None:
            return self.patience
        return max(0.0, self.patience - (self.clock() - self._gone_since))

    def update(self, detected: bool) -> Event:
        """Feed one frame's detection result; return any state transition."""
        self._history.appendleft(detected)
        hits = sum(self._history)

        if not self.active:
            if hits == self.detection_thresh:
                self.active = True
                self._gone_since = None
                return Event.STARTED
            return Event.NONE

        if hits > self.detection_thresh / 2:
            # Subject still (mostly) present - keep the event alive.
            self._gone_since = None
            return Event.NONE

        if self._gone_since is None:
            self._gone_since = self.clock()
        elif self.clock() - self._gone_since >= self.patience:
            self.active = False
            self._gone_since = None
            return Event.ENDED
        return Event.NONE
