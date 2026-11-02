"""Короткие звуки интерфейса: щелчок кнопки и мягкое подтверждение."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

from mapknowlage.paths import asset_dir


class Sounds:
    def __init__(self) -> None:
        self.enabled = True
        folder = asset_dir() / "sounds"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            _write_click(folder / "click.wav")
            _write_confirm(folder / "open.wav")
        except OSError:
            pass
        self._effects: dict[str, QSoundEffect] = {}
        for name in ("click", "open"):
            path = folder / f"{name}.wav"
            if not path.exists():
                continue
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(path)))
            effect.setVolume(0.42)
            self._effects[name] = effect

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        effect = self._effects.get(name)
        if effect is not None:
            effect.play()


def _write_click(path: Path) -> None:
    rate = 44100
    count = int(rate * 0.05)
    rng = random.Random(7)
    frames = bytearray()
    for index in range(count):
        t = index / rate
        attack = 1 - math.exp(-t * 2500)
        envelope = attack * math.exp(-t * 62)
        frequency = 1480 - t * 14000
        tone = math.sin(2 * math.pi * frequency * t)
        noise = rng.uniform(-1, 1)
        sample = (tone * 0.62 + noise * 0.22) * envelope * 0.42
        frames += struct.pack("<h", _sample(sample))
    _save(path, rate, frames)


def _write_confirm(path: Path) -> None:
    rate = 44100
    count = int(rate * 0.28)
    frames = bytearray()
    notes = ((523.25, 0.0, 0.18, 0.34), (659.25, 0.055, 0.2, 0.28), (783.99, 0.11, 0.18, 0.2))
    for index in range(count):
        t = index / rate
        sample = 0.0
        for frequency, start, duration, gain in notes:
            sample += gain * _note(t, frequency, start, duration)
        frames += struct.pack("<h", _sample(sample))
    _save(path, rate, frames)


def _note(t: float, frequency: float, start: float, duration: float) -> float:
    if t < start or t > start + duration:
        return 0.0
    local = (t - start) / duration
    envelope = math.sin(math.pi * local) * math.exp(-local * 1.6)
    return math.sin(2 * math.pi * frequency * (t - start)) * envelope


def _sample(value: float) -> int:
    return int(max(-1.0, min(1.0, value)) * 32000)


def _save(path: Path, rate: int, frames: bytearray) -> None:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
