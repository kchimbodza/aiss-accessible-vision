from aiss.detector import Event, IntrusionMonitor, MotionDetector


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def warm_up(det, make_scene, n=30):
    for t in range(n):
        assert det.detect(make_scene(t)) is None


def test_static_scene_has_no_motion(make_scene):
    warm_up(MotionDetector(history=50), make_scene)


def test_moving_object_is_boxed(make_scene):
    det = MotionDetector(history=50)
    warm_up(det, make_scene)
    bbox = det.detect(make_scene(31, square_at=(100, 80)))
    assert bbox is not None
    x, y, w, h = bbox
    # dilation grows the box a little, but it must contain the object
    assert x <= 100 and y <= 80 and x + w >= 140 and y + h >= 140


def test_small_noise_is_ignored(make_scene):
    det = MotionDetector(history=50, min_area=1e6)
    warm_up(det, make_scene)
    assert det.detect(make_scene(31, square_at=(100, 80))) is None


def test_event_requires_consecutive_detections():
    mon = IntrusionMonitor(detection_thresh=5, patience=2, clock=FakeClock())
    assert [mon.update(True) for _ in range(4)] == [Event.NONE] * 4
    mon.update(False)  # a single miss resets the streak
    assert [mon.update(True) for _ in range(4)] == [Event.NONE] * 4
    assert mon.update(True) is Event.STARTED and mon.active


def test_event_ends_after_patience():
    clock = FakeClock()
    mon = IntrusionMonitor(detection_thresh=4, patience=7, clock=clock)
    for _ in range(4):
        mon.update(True)
    assert mon.active
    for _ in range(4):           # subject leaves -> timer starts
        assert mon.update(False) is Event.NONE
    clock.t = 6.9
    assert mon.update(False) is Event.NONE and mon.active
    assert 0 < mon.patience_left < 0.2
    clock.t = 7.0
    assert mon.update(False) is Event.ENDED and not mon.active


def test_brief_return_resets_patience():
    clock = FakeClock()
    mon = IntrusionMonitor(detection_thresh=4, patience=7, clock=clock)
    for _ in range(4):
        mon.update(True)
    for _ in range(4):
        mon.update(False)
    clock.t = 5
    for _ in range(4):           # subject comes back
        mon.update(True)
    assert mon.patience_left == 7
    clock.t = 20
    assert mon.active
