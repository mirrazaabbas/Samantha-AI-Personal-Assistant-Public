"""Microphone recording with silence detection and audio playback helpers."""

from __future__ import annotations

import io
import wave
from collections.abc import Callable

_SAMPLE_RATE = 16000
_CHANNELS = 1
_CHUNK = 512
_SILENCE_THRESHOLD = 100  # RMS below this → silence
_SILENCE_SECONDS = 0.5  # seconds of silence before auto-stop
_STARTUP_SILENCE_SECONDS = 5.0  # give up early if speech never begins
_MAX_RECORD_SECONDS = 30  # safety ceiling
_SPEECH_START_CHUNKS = 3  # require sustained sound before accepting speech


def _rms(data: bytes) -> float:
    """Compute RMS amplitude of 16-bit PCM bytes."""
    import struct

    n = len(data) // 2
    if n == 0:
        return 0.0
    shorts = struct.unpack(f"{n}h", data[: n * 2])
    return (sum(s * s for s in shorts) / n) ** 0.5


def record_until_silence(
    *,
    sample_rate: int = _SAMPLE_RATE,
    silence_threshold: int = _SILENCE_THRESHOLD,
    silence_seconds: float = _SILENCE_SECONDS,
    startup_silence_seconds: float = _STARTUP_SILENCE_SECONDS,
    max_seconds: float = _MAX_RECORD_SECONDS,
    keep_waiting_on_silence: bool = True,
    on_speech_start: Callable[[], None] | None = None,
) -> bytes:
    """Record from the default microphone until silence is detected.

    Returns raw WAV bytes (16-bit mono).
    Raises RuntimeError if sounddevice is not installed.
    """
    try:
        import sounddevice as sd
    except ImportError:
        raise RuntimeError(
            "sounddevice is required for voice input. "
            "Install with: pip install sounddevice"
        )

    chunks_per_second = sample_rate / _CHUNK
    silence_chunks = max(1, int(silence_seconds * chunks_per_second))
    startup_silence_chunks = max(1, int(startup_silence_seconds * chunks_per_second))
    max_chunks = int(max_seconds * chunks_per_second)

    frames: list[bytes] = []
    silence_count = 0
    startup_silence_count = 0
    speech_start_count = 0
    has_speech = False

    with sd.RawInputStream(
        samplerate=sample_rate,
        channels=_CHANNELS,
        dtype="int16",
        blocksize=_CHUNK,
    ) as stream:
        for _ in range(max_chunks):
            raw, _ = stream.read(_CHUNK)
            data = bytes(raw)
            frames.append(data)
            amplitude = _rms(data)

            if not has_speech:
                if amplitude > silence_threshold:
                    # Speech has started, so startup silence timeout resets.
                    startup_silence_count = 0
                    speech_start_count += 1

                    if speech_start_count >= _SPEECH_START_CHUNKS:
                        has_speech = True
                        silence_count = 0
                        if on_speech_start is not None:
                            # Exclude accumulated room noise and playback echo;
                            # retain only the chunks that triggered speech.
                            frames = frames[-_SPEECH_START_CHUNKS:]
                            on_speech_start()
                else:
                    # Only consecutive silence before speech counts toward
                    # the startup timeout.
                    startup_silence_count += 1
                    speech_start_count = 0

                if not has_speech and startup_silence_count >= startup_silence_chunks:
                    if keep_waiting_on_silence:
                        # While continuously listening, silence is not a command.
                        frames.clear()
                        startup_silence_count = 0
                        speech_start_count = 0
                        continue

                    # After a wake word, silence means no command was given.
                    frames.clear()
                    break

            elif amplitude > silence_threshold:
                silence_count = 0

            else:
                silence_count += 1
                if silence_count >= silence_chunks:
                    break

    return _frames_to_wav(frames, sample_rate)


def _frames_to_wav(frames: list[bytes], sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


def play_wav(audio: bytes, sample_rate: int = 24000) -> None:
    """Play Samantha's WAV audio using macOS afplay."""
    import os
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False,
    ) as tmp:
        tmp.write(audio)
        tmp_path = tmp.name

    try:
        subprocess.run(
            ["/usr/bin/afplay", tmp_path],
            check=False,
            timeout=120,
        )

        # Let speaker echo disappear before hands-free listening resumes.
        import time

        time.sleep(0.7)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def play_wav_interruptible(
    audio: bytes,
    *,
    duration_seconds: float,
    interruption_threshold: int = 2500,
) -> bytes | None:
    """Play WAV audio while listening for a loud nearby interruption.

    Returns the captured interruption WAV, or ``None`` when playback finishes.
    A deliberately high threshold reduces false interruption from speaker echo.
    """
    import os
    import subprocess
    import tempfile
    import threading

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio)
        tmp_path = tmp.name

    interrupted = threading.Event()
    process = subprocess.Popen(  # noqa: S603
        ["/usr/bin/afplay", tmp_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def stop_playback() -> None:
        interrupted.set()
        if process.poll() is None:
            process.terminate()

    try:
        captured = record_until_silence(
            silence_threshold=interruption_threshold,
            silence_seconds=0.4,
            startup_silence_seconds=max(1.0, duration_seconds + 0.5),
            max_seconds=max(1.0, duration_seconds + 0.5),
            keep_waiting_on_silence=True,
            on_speech_start=stop_playback,
        )
        if process.poll() is None:
            process.wait(timeout=2)
        return captured if interrupted.is_set() else None
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


__all__ = [
    "play_wav",
    "play_wav_interruptible",
    "record_until_silence",
    "wait_for_wake_word",
]

_WAKE_MODEL = None


def wait_for_wake_word(
    *,
    wake_word: str = "hey_samantha",
    threshold: float = 0.5,
) -> None:
    """Listen locally until the configured wake word is detected."""
    global _WAKE_MODEL

    try:
        import numpy as np
        import sounddevice as sd
        from openwakeword.model import Model
    except ImportError as exc:
        raise RuntimeError(
            "openwakeword, numpy, and sounddevice are required for wake-word detection."
        ) from exc

    if _WAKE_MODEL is None:
        _WAKE_MODEL = Model(wakeword_models=[wake_word])

    blocksize = 1280

    with sd.InputStream(
        channels=1,
        samplerate=_SAMPLE_RATE,
        dtype="int16",
        blocksize=blocksize,
    ) as stream:
        while True:
            audio, _ = stream.read(blocksize)
            pcm = np.asarray(audio[:, 0], dtype=np.int16)

            prediction = _WAKE_MODEL.predict(pcm)
            score = float(prediction.get(wake_word, 0.0))

            if score >= threshold:
                return
