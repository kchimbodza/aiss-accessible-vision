import cv2

from aiss.detector import IntrusionMonitor, MotionDetector
from aiss.pipeline import run_intrusion


class RecordingNotifier:
    def __init__(self):
        self.messages = []

    def send(self, body):
        self.messages.append(body)


def test_end_to_end_on_video_file(tmp_path, make_scene):
    src = tmp_path / "input.avi"
    w = cv2.VideoWriter(str(src), cv2.VideoWriter_fourcc(*"MJPG"), 20, (320, 240))
    frames = [make_scene(t) for t in range(40)]
    frames += [make_scene(t, square_at=(20 + 4 * t, 80)) for t in range(30)]
    frames += [make_scene(t) for t in range(30)]
    for f in frames:
        w.write(f)
    w.release()

    notifier = RecordingNotifier()
    out = tmp_path / "intrusions"
    events = run_intrusion(
        "Cam1", str(src), out, notifier, frame_size=(320, 240), display=False,
        detector=MotionDetector(history=50, min_area=500),
        monitor=IntrusionMonitor(detection_thresh=5, patience=0),
    )

    assert events == 1
    assert len(notifier.messages) == 1 and "Cam1" in notifier.messages[0]
    clips = list(out.glob("IDS_Cam1_*.mp4"))
    assert len(clips) == 1 and clips[0].stat().st_size > 0
