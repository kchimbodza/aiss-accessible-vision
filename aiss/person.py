"""Deep-learning person detector (NanoDet-Plus, COCO-pretrained, run with OpenCV DNN).

Used as a second stage behind the motion detector: motion is cheap and runs on
every frame, the neural network only runs when something moved, and an alert
is raised only when the network confirms a *person*. This filters out the
false positives a pure motion detector produces (pets, shadows, curtains,
lighting changes, a bumped camera).

The model is not trained by this project. It is NanoDet-Plus-m (416x416) from
the OpenCV Model Zoo, licensed Apache 2.0. The decoding logic below is adapted
from the zoo's reference implementation (opencv_zoo/models/object_detection_nanodet,
Apache 2.0).
"""

from __future__ import annotations

import hashlib
import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)

MODEL_URL = ("https://huggingface.co/opencv/object_detection_nanodet/resolve/main/"
             "object_detection_nanodet_2022nov.onnx")
MODEL_SHA256 = "4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186"
PERSON = 0  # COCO class id

BBox = Tuple[int, int, int, int]


def model_path() -> Path:
    """Where the model lives: $AISS_MODEL, else the user cache directory."""
    if os.getenv("AISS_MODEL"):
        return Path(os.environ["AISS_MODEL"])
    cache = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "aiss"
    return cache / "nanodet_2022nov.onnx"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_model(path: Optional[Path] = None) -> Path:
    """Download the model once (3.8 MB) and verify its checksum."""
    path = path or model_path()
    if path.exists() and _sha256(path) == MODEL_SHA256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    log.info("Downloading person-detection model to %s", path)
    urllib.request.urlretrieve(MODEL_URL, tmp)
    digest = _sha256(tmp)
    if digest != MODEL_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Model checksum mismatch ({digest}); refusing to use it")
    tmp.replace(path)
    return path


@dataclass
class Detection:
    bbox: BBox          # x, y, w, h in original frame pixels
    confidence: float


class PersonDetector:
    """NanoDet-Plus person detector. ``detect(frame)`` returns people found."""

    INPUT = 416
    REG_MAX = 7
    MEAN = np.array([103.53, 116.28, 123.675], dtype=np.float32).reshape(1, 1, 3)
    STD = np.array([57.375, 57.12, 58.395], dtype=np.float32).reshape(1, 1, 3)

    def __init__(self, model: Optional[Path] = None, min_confidence: float = 0.45, nms_iou: float = 0.6):
        self.min_confidence = min_confidence
        self.nms_iou = nms_iou
        self.net = cv2.dnn.readNet(str(model or ensure_model()))
        self._project = np.arange(self.REG_MAX + 1, dtype=np.float32)
        self._anchor_cache = {}

    def _anchors(self, stride: int) -> np.ndarray:
        if stride not in self._anchor_cache:
            n = self.INPUT // stride
            xv, yv = np.meshgrid(np.arange(n) * stride, np.arange(n) * stride)
            self._anchor_cache[stride] = np.column_stack((xv.ravel() + 0.5 * (stride - 1), yv.ravel() + 0.5 * (stride - 1)))
        return self._anchor_cache[stride]

    def _levels(self, outs):
        """Pair class and box outputs by feature-map size.

        OpenCV 4 returns them interleaved, OpenCV 5 returns them grouped, so
        match on shape rather than position. Box outputs have 4*(REG_MAX+1) channels.
        """
        reg_ch = 4 * (self.REG_MAX + 1)
        flat = [o.reshape(-1, o.shape[-1]) for o in outs]
        cls = {o.shape[0]: o for o in flat if o.shape[1] != reg_ch}
        reg = {o.shape[0]: o for o in flat if o.shape[1] == reg_ch}
        for n in sorted(cls, reverse=True):
            if n in reg:
                stride = int(round(self.INPUT / np.sqrt(n)))
                yield stride, cls[n], reg[n], self._anchors(stride)

    def _letterbox(self, frame: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        """Resize keeping aspect ratio and pad to a square model input."""
        h, w = frame.shape[:2]
        scale = self.INPUT / max(h, w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        canvas = np.zeros((self.INPUT, self.INPUT, 3), dtype=np.uint8)
        top, left = (self.INPUT - nh) // 2, (self.INPUT - nw) // 2
        canvas[top:top + nh, left:left + nw] = cv2.resize(frame, (nw, nh))
        return canvas, scale, left, top

    def detect(self, frame: np.ndarray) -> List[Detection]:
        img, scale, left, top = self._letterbox(frame)
        blob = cv2.dnn.blobFromImage((img.astype(np.float32) - self.MEAN) / self.STD)
        self.net.setInput(blob)
        outs = self.net.forward(self.net.getUnconnectedOutLayersNames())

        boxes, scores = [], []
        for stride, cls, reg, anchors in self._levels(outs):
            person = cls[:, PERSON]
            keep = person >= self.min_confidence
            if not keep.any():
                continue
            # Each box side is predicted as a distribution over 0..REG_MAX bins (softmax -> expectation).
            d = np.exp(reg[keep].reshape(-1, self.REG_MAX + 1))
            d = (d / d.sum(axis=1, keepdims=True)) @ self._project
            d = d.reshape(-1, 4) * stride
            a = anchors[keep]
            x1, y1, x2, y2 = a[:, 0] - d[:, 0], a[:, 1] - d[:, 1], a[:, 0] + d[:, 2], a[:, 1] + d[:, 3]
            boxes.append(np.column_stack([x1, y1, x2 - x1, y2 - y1]))
            scores.append(person[keep])
        if not boxes:
            return []
        boxes, scores = np.concatenate(boxes), np.concatenate(scores)
        idx = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), self.min_confidence, self.nms_iou)

        fh, fw = frame.shape[:2]
        found = []
        for i in np.array(idx).reshape(-1):
            x, y, w, h = boxes[i]
            x0 = int(max(0, (x - left) / scale)); y0 = int(max(0, (y - top) / scale))
            x1 = int(min(fw, (x + w - left) / scale)); y1 = int(min(fh, (y + h - top) / scale))
            if x1 > x0 and y1 > y0:
                found.append(Detection((x0, y0, x1 - x0, y1 - y0), float(scores[i])))
        return sorted(found, key=lambda d: d.confidence, reverse=True)


class HybridDetector:
    """Motion first, then a neural-network check that the moving thing is a person.

    * ``mode="hybrid"`` (default): background subtraction runs on every frame; the
      network runs only while there is motion, at most every ``every`` frames.
    * ``mode="person"``: the network runs every ``every`` frames regardless of motion
      (catches someone standing still, costs more CPU).

    ``detect(frame)`` keeps the same contract as :class:`~aiss.detector.MotionDetector`:
    a bounding box when a person is present, else ``None``. ``label`` describes the
    last result for the on-screen display.
    """

    kind = "person"

    def __init__(self, motion, person, mode: str = "hybrid", every: int = 3):
        if mode not in ("hybrid", "person"):
            raise ValueError(f"unknown mode {mode!r}")
        self.motion, self.person, self.mode, self.every = motion, person, mode, max(1, every)
        self._frame = 0
        self._last: Optional[Detection] = None
        self.label = "Person"
        self.network_runs = 0

    def detect(self, frame: np.ndarray) -> Optional[BBox]:
        self._frame += 1
        moving = self.motion.detect(frame)       # always run: keeps the background model current
        if self.mode == "hybrid" and moving is None:
            self._last = None
            return None
        if self._last is None or self._frame % self.every == 0:
            found = self.person.detect(frame)
            self.network_runs += 1
            self._last = found[0] if found else None
        if self._last is None:
            return None
        self.label = f"Person {self._last.confidence:.0%}"
        return self._last.bbox


def build_detector(mode: str, motion, min_confidence: float = 0.45, every: int = 3):
    """Return a detector for ``mode`` (motion | hybrid | person).

    If the model can't be loaded (e.g. offline on first run), fall back to motion
    detection and say so, rather than leaving the camera unwatched.
    """
    if mode == "motion":
        return motion
    try:
        return HybridDetector(motion, PersonDetector(min_confidence=min_confidence), mode, every)
    except Exception as e:  # network, checksum or model errors
        log.warning("Person detector unavailable (%s) - falling back to motion detection", e)
        return motion
