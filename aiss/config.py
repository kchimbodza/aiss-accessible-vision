"""Runtime configuration, read from environment variables (or a ``.env`` file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Union

try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

Source = Union[int, str]


def parse_source(value: str) -> Source:
    """``"0"`` -> webcam index 0; anything else (URL / file path) is kept as-is."""
    value = value.strip()
    return int(value) if value.isdigit() else value


@dataclass
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_number: str
    to_number: str

    @classmethod
    def from_env(cls) -> Optional["TwilioConfig"]:
        keys = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "ALERT_TO_NUMBER")
        values = [os.getenv(k, "").strip() for k in keys]
        return cls(*values) if all(values) else None


@dataclass
class Config:
    cameras: Dict[str, Source] = field(default_factory=dict)
    footage_dir: Path = Path("footage")
    intrusions_dir: Path = Path("intrusions")
    frame_size: tuple = (640, 480)
    fps: float = 20.0
    twilio: Optional[TwilioConfig] = None

    @classmethod
    def from_env(cls) -> "Config":
        cameras = {
            "Cam1": parse_source(os.getenv("AISS_CAM1", "0")),
        }
        if os.getenv("AISS_CAM2"):
            cameras["Cam2"] = parse_source(os.environ["AISS_CAM2"])
        w, h = (int(v) for v in os.getenv("AISS_FRAME_SIZE", "640x480").lower().split("x"))
        return cls(
            cameras=cameras,
            footage_dir=Path(os.getenv("AISS_FOOTAGE_DIR", "footage")),
            intrusions_dir=Path(os.getenv("AISS_INTRUSIONS_DIR", "intrusions")),
            frame_size=(w, h),
            fps=float(os.getenv("AISS_FPS", "20")),
            twilio=TwilioConfig.from_env(),
        )
