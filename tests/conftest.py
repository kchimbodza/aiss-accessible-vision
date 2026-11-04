import numpy as np
import pytest


def scene(t: int, square_at=None, size=(240, 320)):
    """Static noisy-ish background with an optional moving bright square."""
    rng = np.random.default_rng(0)  # same background every frame
    frame = (rng.integers(40, 60, (*size, 3))).astype(np.uint8)
    if square_at is not None:
        x, y = square_at
        frame[y:y + 60, x:x + 40] = 230
    return frame


@pytest.fixture
def make_scene():
    return scene
