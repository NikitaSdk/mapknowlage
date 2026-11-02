"""Круглые портреты: фотография, если она лежит в assets/portraits, иначе вензель."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtGui import QPixmap

from mapknowlage.paths import asset_dir

SIZE = 256


def load_portrait(author_id: str, name: str, zone_color: str) -> QPixmap:
    folder = asset_dir() / "portraits"
    for extension in (".png", ".jpg", ".jpeg", ".webp"):
        path = folder / f"{author_id}{extension}"
        if path.exists():
            image = Image.open(path).convert("RGBA")
            return _pixmap(_circle_photo(image))
    return _pixmap(_medallion(name, zone_color))


def _circle_photo(image: Image.Image) -> Image.Image:
    image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse((4, 4, SIZE - 5, SIZE - 5), fill=255)
    image.putalpha(mask)
    return image


def _medallion(name: str, zone_color: str) -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, SIZE - 3, SIZE - 3), fill=(244, 230, 196, 255))
    color = _hex(zone_color)
    tint = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(tint).ellipse((22, 22, SIZE - 23, SIZE - 23), fill=(*color, 78))
    image = Image.alpha_composite(image, tint)
    draw = ImageDraw.Draw(image)
    initials = "".join(part[0] for part in name.split()[:2])
    font = _font(92 if len(initials) == 1 else 68)
    bbox = draw.textbbox((0, 0), initials, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text(
        ((SIZE - width) / 2 - bbox[0], (SIZE - height) / 2 - bbox[1] - 6),
        initials,
        fill=(43, 30, 18, 255),
        font=font,
    )
    return image


def _font(size: int) -> ImageFont.ImageFont:
    path = asset_dir() / "fonts" / "JetBrainsMono-Regular.ttf"
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _pixmap(image: Image.Image) -> QPixmap:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap
