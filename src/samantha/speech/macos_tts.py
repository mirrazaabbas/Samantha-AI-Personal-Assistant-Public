"""Native macOS text-to-speech backend using ``say`` and ``afconvert``."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from samantha.core.registry import TTSRegistry
from samantha.speech.tts import TTSBackend, TTSResult


@TTSRegistry.register("macos")
class MacOSTTSBackend(TTSBackend):
    """Fast, private TTS using tools included with macOS."""

    backend_id = "macos"

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str = "",
        speed: float = 1.0,
        output_format: str = "wav",
    ) -> TTSResult:
        if not text.strip():
            raise ValueError("text is required")
        if not self.health():
            raise RuntimeError("macOS say/afconvert commands are unavailable")

        rate = max(80, min(500, round(180 * float(speed))))
        voice = voice_id.strip()
        with tempfile.TemporaryDirectory(prefix="samantha-macos-tts-") as tmp:
            source = Path(tmp) / "speech.aiff"
            output = Path(tmp) / "speech.wav"
            command = ["/usr/bin/say", "-r", str(rate), "-o", str(source)]
            if voice:
                command[1:1] = ["-v", voice]
            command.append(text)
            subprocess.run(command, check=True, capture_output=True, timeout=120)
            subprocess.run(
                [
                    "/usr/bin/afconvert",
                    "-f",
                    "WAVE",
                    "-d",
                    "LEI16@24000",
                    str(source),
                    str(output),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            audio = output.read_bytes()
            duration = 0.0
            try:
                with wave.open(str(output), "rb") as wav_file:
                    duration = wav_file.getnframes() / wav_file.getframerate()
            except (OSError, EOFError, wave.Error):
                pass
            if duration <= 0:
                raise RuntimeError(
                    "macOS speech synthesis produced no audio. Check that this "
                    "process has access to an audio output device."
                )
        return TTSResult(
            audio=audio,
            format="wav",
            duration_seconds=duration,
            voice_id=voice or "system-default",
            sample_rate=24000,
            metadata={"local": True},
        )

    def available_voices(self) -> list[str]:
        if shutil.which("say") is None:
            return []
        result = subprocess.run(
            ["/usr/bin/say", "-v", "?"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [line.split(maxsplit=1)[0] for line in result.stdout.splitlines()]

    def health(self) -> bool:
        return shutil.which("say") is not None and shutil.which("afconvert") is not None


__all__ = ["MacOSTTSBackend"]
