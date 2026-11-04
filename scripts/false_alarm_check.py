"""Replay the false-alarm cases from the 2022 field trials on an empty scene.

All 3 false positives in the dissertation's 100 trials came from a bumped camera.
This script simulates that (and a sudden lighting change) on a scene with nobody
in it, and counts how many intrusion events each detector raises.

    python scripts/false_alarm_check.py tests/data/empty-scene.jpg

The input should show a real background with no people in it.
"""
import sys

import cv2
import numpy as np

from aiss.detector import Event, IntrusionMonitor, MotionDetector
from aiss.person import HybridDetector, PersonDetector, ensure_model


def frames(bg, n_warm=60):
    h, w = bg.shape[:2]
    for _ in range(n_warm):                                   # steady scene
        yield "steady", bg
    for i in range(25):                                       # camera bumped: shakes, settles 3px off
        dx, dy = (6, 4) if i < 12 and i % 2 == 0 else (3, 2)
        m = np.float32([[1, 0, dx], [0, 1, dy]])
        yield "bump", cv2.warpAffine(bg, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    for _ in range(25):                                       # lights switched on
        yield "light", cv2.convertScaleAbs(bg, alpha=1.35, beta=25)


def count_events(detector, bg):
    mon = IntrusionMonitor(detection_thresh=5, patience=0)
    events, causes = 0, []
    for cause, f in frames(bg):
        if mon.update(detector.detect(f) is not None) is Event.STARTED:
            events += 1
            causes.append(cause)
    return events, causes


if __name__ == "__main__":
    bg = cv2.imread(sys.argv[1])
    motion = count_events(MotionDetector(history=50), bg)
    hybrid = count_events(HybridDetector(MotionDetector(history=50), PersonDetector(ensure_model()), every=1), bg)
    print(f"motion only : {motion[0]} false alarm(s) {motion[1]}")
    print(f"hybrid      : {hybrid[0]} false alarm(s) {hybrid[1]}")
