"""Command-line entry point: ``aiss gui | live | detect``."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from aiss import __version__
from aiss.config import Config, parse_source
from aiss.detector import IntrusionMonitor, MotionDetector
from aiss.notifier import Notifier
from aiss.person import build_detector


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aiss", description="AI Surveillance System")
    p.add_argument("--version", action="version", version=f"aiss {__version__}")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("gui", help="launch the control panel (default)")

    for name, help_ in (("live", "continuously record a camera"),
                        ("detect", "run intrusion detection on a camera or video file")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("--source", default="0",
                       help="webcam index, IP-camera URL (e.g. http://192.168.1.10:8080/video) or video file")
        s.add_argument("--camera", default="Cam1", help="camera label used in file names / alerts")
        s.add_argument("--out", type=Path, help="output directory for recordings")
        s.add_argument("--no-display", action="store_true", help="run headless (no preview window)")
        if name == "detect":
            s.add_argument("--min-area", type=float, default=1100, help="min contour area in px")
            s.add_argument("--detector", choices=["motion", "hybrid", "person"],
                           help="motion only, motion + neural-net person check (default), or person check on every few frames")
            s.add_argument("--person-confidence", type=float, help="min person confidence 0-1 (default 0.45)")
            s.add_argument("--confirm-frames", type=int, default=15,
                           help="consecutive detections needed to start an event")
            s.add_argument("--patience", type=float, default=7.0,
                           help="seconds without activity before an event ends")
    return p


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    cfg = Config.from_env()

    if args.command in (None, "gui"):
        from aiss.gui import main as gui_main

        gui_main(cfg)
        return 0

    from aiss.pipeline import run_intrusion, run_live

    source = parse_source(args.source)
    if args.command == "live":
        run_live(args.camera, source, args.out or cfg.footage_dir, cfg.fps, cfg.frame_size,
                 display=not args.no_display)
    else:
        n = run_intrusion(
            args.camera, source, args.out or cfg.intrusions_dir, Notifier(cfg.twilio),
            cfg.fps, cfg.frame_size, display=not args.no_display,
            detector=build_detector(args.detector or cfg.detector, MotionDetector(min_area=args.min_area),
                                    args.person_confidence or cfg.person_confidence),
            monitor=IntrusionMonitor(detection_thresh=args.confirm_frames, patience=args.patience),
        )
        logging.info("%d intrusion event(s) recorded", n)
    return 0
