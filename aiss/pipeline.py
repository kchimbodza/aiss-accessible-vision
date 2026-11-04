"""Camera pipelines: continuous live recording and intrusion detection."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2

from aiss import overlay
from aiss.config import Source
from aiss.detector import Event, IntrusionMonitor, MotionDetector
from aiss.notifier import Notifier

log = logging.getLogger(__name__)
ESC = 27
STAMP = "%a-%H-%M-%S_%d-%b-%Y"


def open_camera(source: Source, frame_size) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source {source!r}")
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_size[1])
    return cap


def make_writer(path: Path, fps: float, frame_size) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    return cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, frame_size)


def _show(window: str, frame, display: bool) -> bool:
    """Show frame; return False when the user pressed Esc."""
    if not display:
        return True
    cv2.imshow(window, frame)
    return (cv2.waitKey(1) & 0xFF) != ESC


def run_live(camera: str, source: Source, out_dir: Path, fps=20.0, frame_size=(640, 480),
             display=True) -> None:
    """Record a camera continuously to ``out_dir/LS_<cam>_<timestamp>.mp4``."""
    cap = open_camera(source, frame_size)
    writer = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, frame_size)
            if writer is None:
                path = out_dir / f"LS_{camera}_{datetime.now().strftime(STAMP)}.mp4"
                writer = make_writer(path, fps, frame_size)
                log.info("Live recording %s -> %s", camera, path)
            overlay.draw_live(frame, camera)
            writer.write(frame)
            if not _show(f"AISS Live - {camera} (Esc to stop)", frame, display):
                break
    finally:
        cap.release()
        if writer:
            writer.release()
        if display:
            cv2.destroyAllWindows()


def run_intrusion(camera: str, source: Source, out_dir: Path, notifier: Optional[Notifier] = None,
                  fps=20.0, frame_size=(640, 480), display=True,
                  detector: Optional[MotionDetector] = None,
                  monitor: Optional[IntrusionMonitor] = None) -> int:
    """Watch a camera; record a clip and send an alert for every intrusion.

    Returns the number of intrusion events recorded.
    """
    notifier = notifier or Notifier()
    detector = detector or MotionDetector()
    monitor = monitor or IntrusionMonitor()
    cap = open_camera(source, frame_size)
    writer, started_at, events = None, None, 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.resize(frame, frame_size)
            bbox = detector.detect(frame)
            event = monitor.update(bbox is not None)

            if event is Event.STARTED:
                started_at = datetime.now()
                path = out_dir / f"IDS_{camera}_{started_at.strftime(STAMP)}.mp4"
                writer = make_writer(path, fps, frame_size)
                log.info("Intrusion on %s - recording %s", camera, path)
            elif event is Event.ENDED:
                writer.release()
                writer, events = None, events + 1
                ended_at = datetime.now()
                notifier.send(
                    f"AISS alert: activity on {camera} from "
                    f"{started_at:%a %d %b %Y %H:%M:%S} to {ended_at:%H:%M:%S} "
                    f"({(ended_at - started_at).seconds}s recorded)."
                )

            overlay.draw_intrusion(frame, bbox, monitor.active, monitor.patience_left)
            if writer is not None:
                writer.write(frame)
            if not _show(f"AISS Intrusion Detection - {camera} (Esc to stop)", frame, display):
                break
    finally:
        cap.release()
        if writer:
            writer.release()
            events += 1
        if display:
            cv2.destroyAllWindows()
    return events
