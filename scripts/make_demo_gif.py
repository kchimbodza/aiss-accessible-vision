"""Render docs/images/person-detection-demo.gif from OpenCV's public vtest.avi sample.

    curl -LO https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/vtest.avi
    python scripts/make_demo_gif.py vtest.avi
"""
import sys
import cv2
from PIL import Image

from aiss import overlay
from aiss.person import PersonDetector, ensure_model

det = PersonDetector(ensure_model())
cap = cv2.VideoCapture(sys.argv[1])
cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
frames = []
for i in range(150):
    ok, f = cap.read()
    if not ok:
        break
    if i % 3:
        continue
    people = det.detect(f)
    for d in people:
        x, y, w, h = d.bbox
        cv2.rectangle(f, (x, y), (x + w, y + h), overlay.CYAN, 2)
        cv2.putText(f, f"Person {d.confidence:.0%}", (x, max(12, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, overlay.CYAN, 1, cv2.LINE_AA)
    overlay.draw_banner(f)
    overlay._text(f, f"People detected: {len(people)}", (150, 20), overlay.CYAN)
    overlay._text(f, "OpenCV sample video (vtest.avi) - pretrained NanoDet person detector", (20, f.shape[0] - 20))
    rgb = cv2.cvtColor(cv2.resize(f, (480, 360), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    frames.append(Image.fromarray(rgb))
# One shared palette for every frame; per-frame palettes make colours flicker.
palette = frames[len(frames) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
gif = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
gif[0].save("docs/images/person-detection-demo.gif", save_all=True, append_images=gif[1:], duration=150, loop=0)
print(len(frames), "frames")
