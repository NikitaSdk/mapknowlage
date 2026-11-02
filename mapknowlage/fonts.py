"""Книжный шрифт с кириллицей, близкий к пергаментной карточке."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFont, QFontDatabase, QRawFont

from mapknowlage.paths import asset_dir


@dataclass
class FontBook:
    display: str = "Consolas"
    text: str = "Consolas"
    fell: str = "Consolas"


FONTS = FontBook()


def load_fonts() -> FontBook:
    folder = asset_dir() / "fonts"
    families: list[str] = []
    for path in sorted(folder.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    bundled = _pick(families, "Literata", "") or _pick(families, "Source Serif", "")
    if bundled and _has_cyrillic(bundled):
        chosen = bundled
    elif _has_cyrillic("Georgia"):
        chosen = "Georgia"
    elif _has_cyrillic("Palatino Linotype"):
        chosen = "Palatino Linotype"
    elif _has_cyrillic("Times New Roman"):
        chosen = "Times New Roman"
    else:
        chosen = "Georgia"
    FONTS.display = chosen
    FONTS.text = chosen
    FONTS.fell = chosen
    return FONTS


def _pick(families: list[str], needle: str, fallback: str) -> str:
    for family in families:
        if needle.lower() in family.lower():
            return family
    return fallback


def _has_cyrillic(family: str) -> bool:
    raw = QRawFont.fromFont(QFont(family))
    return raw.isValid() and raw.supportsCharacter("П")
