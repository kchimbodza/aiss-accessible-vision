"""Tkinter control panel: start live / intrusion cameras and browse recordings.

Each camera pipeline runs in its own process so several streams can be
recorded and analysed concurrently without blocking the UI.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from multiprocessing import Process
from pathlib import Path

from PIL import Image, ImageTk

from aiss.config import Config
from aiss.notifier import Notifier
from aiss.detector import MotionDetector
from aiss.person import build_detector
from aiss.pipeline import run_intrusion, run_live

ASSETS = Path(__file__).parent / "assets"
WIDTH, HEIGHT = 720, 360
NAVY, WHITE, GREEN = "#2e3192", "#ffffff", "#3DDC84"


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def _live(cfg: Config, cam: str) -> None:
    run_live(cam, cfg.cameras[cam], cfg.footage_dir, cfg.fps, cfg.frame_size)


def _intrusion(cfg: Config, cam: str) -> None:
    detector = build_detector(cfg.detector, MotionDetector(), cfg.person_confidence)
    run_intrusion(cam, cfg.cameras[cam], cfg.intrusions_dir, Notifier(cfg.twilio),
                  cfg.fps, cfg.frame_size, detector=detector)


class ControlPanel:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.procs: list[Process] = []
        self.root = root = tk.Tk()
        root.title("AI SURVEILLANCE SYSTEM (AISS)")
        root.geometry(f"{WIDTH}x{HEIGHT}")
        root.resizable(False, False)
        root.iconphoto(False, tk.PhotoImage(file=str(ASSETS / "icon.png")))
        root.protocol("WM_DELETE_WINDOW", self.quit)

        bg = Image.open(ASSETS / "background.jpg").resize((WIDTH, HEIGHT), Image.LANCZOS)
        self._bg = ImageTk.PhotoImage(bg)
        tk.Label(root, image=self._bg).place(relx=0.5, rely=0.5, anchor="center")

        self.font = tkfont.Font(size=16)
        cams = list(cfg.cameras)
        for i, cam in enumerate(cams[:2]):
            x = 250 + 100 * i
            self._button(cam.replace("Cam", "Cam "), x, 76, lambda c=cam: self.spawn(_live, c))
            self._button(cam.replace("Cam", "Cam "), x, 161, lambda c=cam: self.spawn(_intrusion, c))
        self._button("Footage", 250, 245, lambda: open_folder(cfg.footage_dir), GREEN, width=11)
        self._button("Intrusions", 473, 245, lambda: open_folder(cfg.intrusions_dir), GREEN, width=11)
        self._button("EXIT", 320, 315, self.quit)

    def _button(self, text, x, y, command, color=NAVY, width=4) -> None:
        btn = tk.Button(self.root, text=text, width=width, height=1, fg=WHITE, bg=color,
                        border=0, activeforeground=color, activebackground=WHITE,
                        font=self.font, command=command)
        btn.bind("<Enter>", lambda e: btn.config(bg=WHITE, fg=color))
        btn.bind("<Leave>", lambda e: btn.config(bg=color, fg=WHITE))
        btn.place(x=x, y=y)

    def spawn(self, target, cam: str) -> None:
        proc = Process(target=target, args=(self.cfg, cam), daemon=True)
        proc.start()
        self.procs.append(proc)

    def quit(self) -> None:
        for proc in self.procs:
            if proc.is_alive():
                proc.terminate()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main(cfg: Config | None = None) -> None:
    ControlPanel(cfg or Config.from_env()).run()
