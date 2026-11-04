<div align="center">

# 🎥 AISS: AI Surveillance System

**Accessible, low-cost computer vision security: real-time intrusion detection that turns ordinary webcams and smartphones into a smart CCTV network.**

[![CI](https://github.com/kchimbodza/aiss-accessible-vision/actions/workflows/ci.yml/badge.svg)](https://github.com/kchimbodza/aiss-accessible-vision/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-computer%20vision-5C3EE8?logo=opencv&logoColor=white)
![Deep learning](https://img.shields.io/badge/deep%20learning-person%20detection-FF6F00)
![Twilio](https://img.shields.io/badge/Twilio-SMS%20alerts-F22F46?logo=twilio&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

<img src="docs/images/intrusion-detected.png" width="720" alt="AISS detecting a person and drawing a bounding box">

</div>

---

## Overview

AISS is a computer vision surveillance system I designed, built and field-tested for my
**Bachelor of Information Technology (Honours) research project** at Zimbabwe Open University (2022).
The client was **Cosy Westwood Cottages**, a guest-house business in Harare that had suffered
break-ins and vandalism and could not afford a commercial CCTV installation.

AISS reuses equipment the business already had (a spare laptop, Wi-Fi, webcams and old Android
phones streaming as IP cameras). It does the following:

- **records** every camera continuously, with a timestamped on-screen display
- **detects** intruders in real time: background subtraction spots motion, then a pretrained
  deep-learning model confirms it is a **person** (new in v2.1)
- **saves an evidence clip** of each intrusion, using searchable file names
- **sends an SMS alert** to the owner through the Twilio API when an intrusion ends

### ♿ Accessible by design

Commercial AI surveillance tends to cost too much for small businesses and assume a lot of
technical knowledge. AISS was built to remove those barriers:

- **No new hardware.** It runs on a laptop the client already owned, plus old Android phones
  streaming as IP cameras.
- **Alerts reach any phone.** Notifications are plain SMS, so they work on a basic feature phone
  with no app, smartphone or mobile data needed. That matters in places where data is
  expensive or patchy.
- **No one has to watch screens.** The system does the watching and only raises an alert when
  something happens. It can run unattended.
- **Simple to operate.** One control panel with large, high-contrast buttons. Clips are named by
  camera and time, so non-technical owners can find evidence without scrubbing through footage.
- **Low-bandwidth friendly.** Streams are processed at modest resolutions over local Wi-Fi, and
  nothing is sent to the cloud.

### Results: 100 controlled trials

|                     | Actual activity | No activity |
|---------------------|:---------------:|:-----------:|
| **Alert raised**    | TP = 49         | FP = 3      |
| **No alert**        | FN = 0          | TN = 48     |

| Accuracy | Precision | Recall |
|:--------:|:---------:|:------:|
| **97%**  | **94.2%** | **100%** |

No intrusion was missed. All three false positives happened when a camera was physically bumped.

### v2.1: a neural network that knows what a person looks like

The 2022 system raised an alert for anything that moved. In v2.1, motion only *wakes up* a
pretrained person detector. An alert fires only when the network confirms a person.

<div align="center">
<img src="docs/images/person-detection-demo.gif" width="560" alt="Pretrained person detector boxing pedestrians in OpenCV's sample video">
<br><sub>The person detector running on OpenCV's public <code>vtest.avi</code> sample at about 25 fps on a laptop CPU.</sub>
</div>

I replayed the field trials' false-alarm causes on an empty scene
([`scripts/false_alarm_check.py`](scripts/false_alarm_check.py), also run as a test in CI):

| Scenario (no one in the scene) | Motion only (2022) | Motion + person check (v2.1) |
|---|:---:|:---:|
| Camera bumped | ⚠️ false alarm | ✅ no alarm |
| Lights switched on | ⚠️ false alarm | ✅ no alarm |

This is a synthetic check, not a repeat of the 100 field trials, but it targets exactly the
failure seen in the field.

---

## How it works

```mermaid
flowchart LR
    A[Webcam / IP camera] --> B[MOG2 background<br>subtraction]
    B --> C[Shadow threshold<br>+ dilation]
    C --> D[Largest contour<br>&gt; min area?]
    D -->|motion| P[Pretrained person<br>detector, NanoDet]
    P -->|person found| E{Debounce:<br>15 consecutive hits}
    E -->|event starts| F[Record MP4 clip]
    F --> G{Patience timer:<br>gone for 7 s?}
    G -->|event ends| H[SMS alert via Twilio]
```

1. **Background modelling**: OpenCV's Gaussian Mixture Model (MOG2, Zivkovic 2004/2006) learns
   the static scene, so anything that moves shows up as foreground.
2. **Mask cleanup**: shadow pixels are thresholded out, and morphological dilation merges the
   fragments of a body into one blob.
3. **Contour filtering**: only the largest contour above a minimum area counts, which rejects
   sensor noise and small movements.
4. **Person confirmation** (`HybridDetector`, v2.1): while something is moving, a pretrained
   NanoDet-Plus network (COCO dataset, run through OpenCV's DNN module) checks whether it's a
   person. To save CPU it runs at most every 3rd frame. It needs no GPU or PyTorch, and it
   downloads once (3.8 MB, checked by SHA-256). If the model can't load, AISS falls back to
   motion-only detection rather than leaving the camera unwatched.
5. **Temporal reasoning** (`IntrusionMonitor`): an event starts only after *N consecutive*
   positive frames, and it ends only after the scene has been clear for a *patience* period.
   This keeps alerts from flickering and stops one intrusion from turning into dozens of SMS
   messages.
6. **Concurrency**: each camera runs in its own process, so four streams can be recorded and
   analysed at the same time on one laptop.

<details>
<summary><b>System architecture and flowchart</b> (from the dissertation)</summary>

<img src="docs/images/architecture.png" alt="System architecture">
<img src="docs/images/flowchart.png" alt="Flowchart">

</details>

---

## Screenshots

| Control panel | Four concurrent streams |
|:---:|:---:|
| <img src="docs/images/control-panel.png" width="400"> | <img src="docs/images/four-streams.png" width="400"> |
| **Patience timer counting down** | **SMS alert on the owner's phone** |
| <img src="docs/images/patience-countdown.png" width="400"> | <img src="docs/images/sms-alert.png" width="220"> |

---

## Quick start

```bash
git clone https://github.com/kchimbodza/aiss-accessible-vision.git
cd aiss-accessible-vision
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env        # set camera sources and (optionally) Twilio keys
aiss                        # launch the control panel
```

You can also run each part on its own from the command line:

```bash
aiss live   --source 0                                   # record webcam 0
aiss detect --source http://192.168.1.104:8080/video     # watch a phone streaming as an IP camera
aiss detect --source hallway.mp4 --no-display            # analyse a recorded video headlessly
aiss detect --source 0 --min-area 1500 --confirm-frames 10 --patience 5
aiss detect --source 0 --detector motion                 # 2022 behaviour: alert on any motion
aiss detect --source 0 --detector person                 # also catch someone standing still
```

If Twilio isn't configured, alerts are written to the console instead, so you can try the
system without an account.

### Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `AISS_CAM1`, `AISS_CAM2` | `0`, unset | Webcam index or IP-camera stream URL |
| `AISS_FRAME_SIZE` | `640x480` | Processing and recording resolution |
| `AISS_FOOTAGE_DIR` / `AISS_INTRUSIONS_DIR` | `footage` / `intrusions` | Output folders |
| `AISS_DETECTOR` | `hybrid` | `motion`, `hybrid` (motion + person check) or `person` |
| `AISS_PERSON_CONFIDENCE` | `0.45` | Minimum person confidence (0-1) |
| `AISS_MODEL` | `~/.cache/aiss/…onnx` | Use a local copy of the model (offline installs) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `ALERT_TO_NUMBER` | unset | SMS alerts |

Recordings are named by type, camera and time (for example `LS_Cam1_…mp4` for live
surveillance and `IDS_Cam2_Mon-09-37-02_28-Feb-2022.mp4` for an intrusion). This makes
evidence easy to find without scrubbing through hours of footage.

---

## Project structure

```
aiss/
├── detector.py   # MotionDetector (CV) + IntrusionMonitor (debounce / patience state machine)
├── person.py     # pretrained person detector (NanoDet, OpenCV DNN) + HybridDetector
├── pipeline.py   # live-recording and intrusion-detection camera loops
├── overlay.py    # on-frame HUD (status, patience timer, timestamp, bounding boxes)
├── notifier.py   # non-blocking Twilio SMS, falls back to console logging
├── gui.py        # Tkinter control panel, one process per camera
├── config.py     # .env / environment configuration
└── cli.py        # `aiss gui | live | detect`
scripts/          # false-alarm check and demo GIF generator
tests/            # unit, end-to-end and real-model tests (run in CI, no camera needed)
legacy/           # original 2022 v1.4 source, kept for reference
```

## Testing

```bash
pip install -e ".[dev]"
pytest -v
```

The tests generate synthetic frames and videos, so the detector, the state machine and the full
record-and-alert pipeline can all be checked in CI without camera hardware. The person-detector
tests run the real model on a frame from OpenCV's sample video. They check that pedestrians are
found, that an empty scene stays empty, and that a bumped camera doesn't raise an alarm.

---

## Version history

- **v1.4 (2022)**: the version delivered for the dissertation (see [`legacy/`](legacy)).
- **v2.0 (2026)**: refactored into a tested Python package with a CLI and CI. This version:
  - moves secrets out of the source code and into `.env`
  - replaces four copy-pasted camera loops with one reusable pipeline
  - sends SMS alerts without blocking the video loop
  - works across platforms (Linux, macOS and Windows)
- **v2.1 (2026)**: adds deep-learning person confirmation (pretrained NanoDet through OpenCV DNN).
  Motion alone no longer raises an alert, which removes the bumped-camera and lighting false
  alarms in the synthetic check above.

## Future work

- Re-run the 100 field trials with v2.1 to measure the real-world false-alarm rate
- Fine-tune the person detector on footage from the client's own cameras
- Web dashboard and cloud backup of intrusion clips

## Acknowledgements

- Supervisor: Ms S. Ruzvidzo, Zimbabwe Open University
- The intrusion-detection loop and the Tkinter control panel started from public OpenCV
  learning tutorials (Bleed AI's intruder-detection tutorial and the `smart-cctv-tkinter`
  project). I then adapted them for multiple cameras, the client's requirements and field testing.

- Person detection model: [NanoDet-Plus](https://github.com/RangiLyu/nanodet) via the
  [OpenCV Model Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_nanodet)
  (Apache 2.0). The decoding code in `aiss/person.py` is adapted from the zoo's reference
  implementation. I use the model as published; I didn't train it.
- Demo video and test frames: OpenCV's `vtest.avi` sample (Apache 2.0).

## Author

**Kudzayi Chimbodza**: [GitHub @kchimbodza](https://github.com/kchimbodza)

Licensed under the [MIT License](LICENSE).
