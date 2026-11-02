"""Текстуры моря и зерна пергамента."""

from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtGui import QPixmap


def sea_tile() -> QPixmap:
    return _tile((138, 130, 118), blotches=14, swing=8, seed=2)


def grain_tile() -> QPixmap:
    return _tile((214, 198, 168), blotches=22, swing=12, seed=5)


def _tile(base: tuple[int, int, int], blotches: int, swing: float, seed: int) -> QPixmap:
    rng = np.random.default_rng(seed)
    size = 384
    image = np.empty((size, size, 3), dtype=np.float32)
    image[:] = base
    image += (rng.random((size, size, 1)) - 0.5) * swing
    yy, xx = np.mgrid[0:size, 0:size]
    image += np.sin(xx / 17.0)[..., None] * 1.2
    for _ in range(blotches):
        cx = int(rng.integers(0, size))
        cy = int(rng.integers(0, size))
        radius = int(rng.integers(18, 70))
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 < radius * radius
        image[mask] *= float(rng.uniform(0.9, 1.08))
    data = np.clip(image, 0, 255).astype(np.uint8)
    buffer = Image.fromarray(data, "RGB")
    from io import BytesIO

    raw = BytesIO()
    buffer.save(raw, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(raw.getvalue(), "PNG")
    return pixmap
