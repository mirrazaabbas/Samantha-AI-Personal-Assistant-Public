"""Timing behavior for microphone silence detection."""

from __future__ import annotations

import struct
import sys
from types import SimpleNamespace

from samantha.speech.voice_io import record_until_silence


class _FakeStream:
    def __init__(self, frames: list[bytes]) -> None:
        self.frames = iter(frames)
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return None

    def read(self, chunk: int):
        self.reads += 1
        return next(self.frames), False


def _install_audio(monkeypatch, stream: _FakeStream) -> None:
    fake_sd = SimpleNamespace(RawInputStream=lambda **kwargs: stream)
    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)


def test_initial_silence_stops_at_startup_timeout(monkeypatch) -> None:
    # voice_io reads 512 samples per chunk. At 1024 Hz,
    # each read represents 0.5 seconds, so provide enough
    # frames for the 2-second startup timeout.
    silence = bytes(1024 * 2)
    stream = _FakeStream([silence] * 10)
    _install_audio(monkeypatch, stream)

    record_until_silence(
        sample_rate=1024,
        startup_silence_seconds=2,
        max_seconds=30,
        keep_waiting_on_silence=False,
    )

    assert stream.reads == 4


def test_post_speech_uses_normal_silence_window(monkeypatch) -> None:
    speech = struct.pack("1024h", *([1000] * 1024))
    silence = bytes(1024 * 2)

    # Three consecutive speech chunks are required before speech is
    # accepted, followed by four silence chunks for the 2-second
    # post-speech silence window.
    stream = _FakeStream([speech, speech, speech, silence, silence, silence, silence])
    _install_audio(monkeypatch, stream)

    record_until_silence(
        sample_rate=1024,
        silence_seconds=2,
        startup_silence_seconds=1,
        max_seconds=30,
        keep_waiting_on_silence=False,
    )

    assert stream.reads == 7


def test_speech_start_callback_runs_once(monkeypatch) -> None:
    speech = struct.pack("1024h", *([3000] * 1024))
    silence = bytes(1024 * 2)
    stream = _FakeStream([speech, speech, speech, silence])
    _install_audio(monkeypatch, stream)
    calls = []

    record_until_silence(
        sample_rate=1024,
        silence_seconds=0.5,
        max_seconds=4,
        keep_waiting_on_silence=False,
        on_speech_start=lambda: calls.append(True),
    )

    assert calls == [True]
