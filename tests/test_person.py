from pathlib import Path

import cv2
import numpy as np
import pytest

from aiss import person as P
from aiss.detector import IntrusionMonitor, MotionDetector
from aiss.pipeline import run_intrusion

DATA = Path(__file__).parent / "data"


class StubMotion:
    """Reports motion on the frames listed in ``moving``."""
    def __init__(self, moving):
        self.moving, self.i = set(moving), 0

    def detect(self, frame):
        self.i += 1
        return (10, 10, 50, 80) if self.i in self.moving else None


class StubPerson:
    def __init__(self, people=True):
        self.people, self.calls = people, 0

    def detect(self, frame):
        self.calls += 1
        return [P.Detection((12, 8, 40, 90), 0.87)] if self.people else []


FRAME = np.zeros((240, 320, 3), np.uint8)


def test_no_motion_means_no_network_call():
    det = P.HybridDetector(StubMotion([]), StubPerson(), every=1)
    assert all(det.detect(FRAME) is None for _ in range(10))
    assert det.network_runs == 0


def test_motion_without_person_is_ignored():
    """The pet / shadow / bumped-camera case: motion, but the network sees nobody."""
    det = P.HybridDetector(StubMotion(range(1, 11)), StubPerson(people=False), every=1)
    assert all(det.detect(FRAME) is None for _ in range(10))


def test_motion_with_person_returns_person_box():
    det = P.HybridDetector(StubMotion([1]), StubPerson())
    assert det.detect(FRAME) == (12, 8, 40, 90)
    assert det.label == "Person 87%"


def test_network_is_throttled_while_moving():
    person = StubPerson()
    det = P.HybridDetector(StubMotion(range(1, 13)), person, every=3)
    for _ in range(12):
        det.detect(FRAME)
    assert person.calls == 5   # first moving frame, then frames 3, 6, 9, 12


def test_person_mode_runs_without_motion():
    person = StubPerson()
    det = P.HybridDetector(StubMotion([]), person, mode="person", every=1)
    assert det.detect(FRAME) == (12, 8, 40, 90)


def test_falls_back_to_motion_when_model_missing(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(P, "PersonDetector", boom)
    motion = MotionDetector()
    assert P.build_detector("hybrid", motion) is motion


def test_bad_download_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(P.urllib.request, "urlretrieve", lambda url, dst: Path(dst).write_bytes(b"not a model"))
    target = tmp_path / "m.onnx"
    with pytest.raises(RuntimeError, match="checksum"):
        P.ensure_model(target)
    assert not target.exists() and not target.with_suffix(".part").exists()


def _scene(t, person_at=None):
    rng = np.random.default_rng(0)
    f = rng.integers(40, 60, (240, 320, 3)).astype(np.uint8)
    if person_at is not None:
        x, y = person_at
        f[y:y + 60, x:x + 40] = 230
    return f


@pytest.mark.parametrize("people,events", [(False, 0), (True, 1)])
def test_pipeline_alerts_only_for_people(tmp_path, people, events):
    src = tmp_path / "in.avi"
    w = cv2.VideoWriter(str(src), cv2.VideoWriter_fourcc(*"MJPG"), 20, (320, 240))
    for f in [_scene(t) for t in range(40)] + [_scene(t, (20 + 4 * t, 80)) for t in range(30)] + [_scene(t) for t in range(30)]:
        w.write(f)
    w.release()

    sent = []
    notifier = type("N", (), {"send": lambda self, b: sent.append(b)})()
    det = P.HybridDetector(MotionDetector(history=50, min_area=500), StubPerson(people), every=1)
    n = run_intrusion("Cam1", str(src), tmp_path / "out", notifier, frame_size=(320, 240), display=False,
                      detector=det, monitor=IntrusionMonitor(detection_thresh=5, patience=0))
    assert n == events and len(sent) == events
    if events:
        assert "person detected" in sent[0]


@pytest.fixture(scope="module")
def real_detector():
    try:
        return P.PersonDetector(P.ensure_model())
    except Exception as e:  # no network in this environment
        pytest.skip(f"model unavailable: {e}")


def test_real_model_finds_pedestrians(real_detector):
    frame = cv2.imread(str(DATA / "pedestrians.jpg"))
    found = real_detector.detect(frame)
    assert len(found) >= 3
    h, w = frame.shape[:2]
    for d in found:
        x, y, bw, bh = d.bbox
        assert 0 <= x < w and 0 <= y < h and bh > bw        # people are taller than wide
        assert 0.45 <= d.confidence <= 1


def test_real_model_ignores_empty_scene(real_detector):
    assert real_detector.detect(_scene(0)) == []


def test_hybrid_suppresses_bump_and_lighting_false_alarms(real_detector):
    """The 2022 trials' false positives came from a bumped camera. Motion alone alarms; hybrid must not."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("fac", Path(__file__).parents[1] / "scripts" / "false_alarm_check.py")
    fac = importlib.util.module_from_spec(spec); spec.loader.exec_module(fac)
    bg = cv2.imread(str(DATA / "empty-scene.jpg"))
    motion_events, _ = fac.count_events(MotionDetector(history=50), bg)
    hybrid_events, _ = fac.count_events(P.HybridDetector(MotionDetector(history=50), real_detector, every=1), bg)
    assert motion_events >= 1 and hybrid_events == 0
