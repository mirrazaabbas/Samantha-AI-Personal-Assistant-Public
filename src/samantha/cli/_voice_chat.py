"""Voice input/output helpers for the interactive chat session."""

from __future__ import annotations

from typing import Any, Optional

from rich.markup import escape

VOICE_EXIT = object()

# Samantha stays asleep until the wake word is spoken.
_SAMANTHA_WAITING_FOR_COMMAND = False
_TTS_BACKEND_ORDER = ("macos", "kokoro", "openai_tts", "cartesia")


def _terminal_safe_text(value: object) -> str:
    """Remove terminal controls and escape Rich markup from dynamic text."""
    printable = "".join(
        char for char in str(value) if char in ("\n", "\t") or char.isprintable()
    )
    return escape(printable)


class VoiceSession:
    """Cache healthy speech backends for one interactive chat session."""

    def __init__(self, config: object | None = None) -> None:
        self._config = config
        self._stt_resolved = False
        self._stt_backend: Any = None
        self._tts_backend: Any = None
        self._tts_attempted: set[str] = set()

    def get_stt_backend(self) -> Any:
        """Resolve and health-check STT once, then reuse the loaded backend."""
        if not self._stt_resolved:
            from samantha.core.config import load_config
            from samantha.speech._discovery import get_speech_backend

            config = self._config if self._config is not None else load_config()
            self._stt_backend = get_speech_backend(config)
            self._stt_resolved = True
        return self._stt_backend

    def get_tts_backend(self) -> Any:
        """Return a cached healthy TTS backend, falling through once per key."""
        if self._tts_backend is not None:
            return self._tts_backend

        # Import triggers built-in backend registration only when voice output
        # is actually requested.
        import samantha.speech  # noqa: F401
        from samantha.core.registry import TTSRegistry

        for key in _TTS_BACKEND_ORDER:
            if key in self._tts_attempted:
                continue
            self._tts_attempted.add(key)
            if not TTSRegistry.contains(key):
                continue
            try:
                candidate = TTSRegistry.get(key)()
                if candidate.health():
                    self._tts_backend = candidate
                    return candidate
            except Exception:
                continue
        return None

    def discard_tts_backend(self) -> None:
        """Forget a backend that failed synthesis and allow the next fallback."""
        self._tts_backend = None


def read_voice_input(console: Any, session: VoiceSession) -> Optional[str] | object:
    """Accept a typed command/message, or record after an empty submission."""
    try:
        typed = input("You> [type, or press Enter to speak] ")
    except (EOFError, KeyboardInterrupt):
        return VOICE_EXIT
    typed = typed.strip()
    return typed if typed else record_voice(console, session)


def record_voice(
    console: Any,
    session: VoiceSession | None = None,
) -> Optional[str] | object:
    """Record one command and transcribe it.

    Wake-word detection is handled by the interactive voice loop.
    This helper only handles microphone recording and STT.
    """
    from samantha.speech.voice_io import record_until_silence

    active_session = session or VoiceSession()

    # Resolve STT before opening/using the microphone.
    backend = active_session.get_stt_backend()
    if backend is None:
        console.print("[red]Samantha: No speech-to-text backend available.[/red]")
        return VOICE_EXIT

    console.print("[bold cyan]Samantha:[/bold cyan] Yes, Sir.")
    console.print("[dim cyan]Listening for your command…[/dim cyan]")

    try:
        audio_bytes = record_until_silence(
            keep_waiting_on_silence=False,
        )
    except KeyboardInterrupt:
        return VOICE_EXIT
    except Exception as exc:
        console.print(f"[red]Mic error: {_terminal_safe_text(exc)}[/red]")
        return VOICE_EXIT

    # A real WAV silence capture is normally just its header.
    # Keep the short-buffer guard for actual WAV data, while allowing
    # lightweight test/mocked audio buffers to reach the STT backend.
    if (
        len(audio_bytes) <= 64
        and isinstance(audio_bytes, (bytes, bytearray))
        and bytes(audio_bytes).startswith(b"RIFF")
    ):
        console.print("[dim]No command heard — going back to sleep.[/dim]")
        return None

    console.print("[dim]Transcribing command…[/dim]")

    try:
        result = backend.transcribe(
            audio_bytes,
            format="wav",
            language="en",
        )

        text = result.text.strip()
        if not text:
            console.print("[dim]No command heard — going back to sleep.[/dim]")
            return None

        import re

        normalized = re.sub(
            r"[^a-z0-9 ]+",
            "",
            text.lower(),
        )
        normalized = " ".join(normalized.split())

        wake_prefixes = (
            "hey samantha",
            "heysamantha",
            "hejavis",
        )

        for wake_prefix in wake_prefixes:
            if normalized == wake_prefix:
                console.print(
                    "[dim]Wake phrase only — waiting for the next wake.[/dim]"
                )
                return None

            if normalized.startswith(wake_prefix + " "):
                normalized = normalized[len(wake_prefix) :].strip()
                text = re.sub(
                    r"^\s*(?:hey\s+samantha|heysamantha|hejavis)"
                    r"[\s,.:;!?-]*",
                    "",
                    text,
                    flags=re.IGNORECASE,
                ).strip()
                break

        if not normalized or not text:
            return None

        console.print(f"[bold]You (voice):[/bold] {_terminal_safe_text(text)}")

        stop_phrases = {
            "stop",
            "quit",
            "exit",
            "stop listening",
            "go offline",
            "shut down",
            "samantha stop",
            "samantha quit",
            "samantha exit",
            "samantha stop listening",
            "samantha go offline",
            "samantha shut down",
            "goodbye samantha",
            "please stop",
            "please quit",
        }

        stop_command = normalized in stop_phrases

        if (
            normalized.endswith(" stop")
            or normalized.endswith(" quit")
            or normalized.endswith(" exit")
        ):
            stop_command = True

        words = normalized.split()
        if words:
            if words[0] == "samantha":
                words = words[1:]

            if words and (
                words[0].startswith("stop")
                or words[0].startswith("quit")
                or words[0].startswith("exit")
            ):
                stop_command = True

        if stop_command:
            console.print("[bold cyan]Samantha:[/bold cyan] Goodbye Sir.")
            return VOICE_EXIT

        return text

    except Exception as exc:
        console.print(f"[red]Transcription error: {_terminal_safe_text(exc)}[/red]")
        return None


def speak(text: str, console: Any, session: VoiceSession | None = None) -> None:
    """Synthesize and play text, reusing a healthy backend for the session."""
    from samantha.speech.voice_io import play_wav

    active_session = session or VoiceSession()
    while (backend := active_session.get_tts_backend()) is not None:
        try:
            result = backend.synthesize(text, output_format="wav")
            if result.audio:
                play_wav(result.audio, sample_rate=result.sample_rate)
            return
        except Exception:
            active_session.discard_tts_backend()

    console.print(
        "[dim yellow]No TTS backend available — install kokoro: "
        "pip install kokoro[/dim yellow]"
    )


__all__ = ["VOICE_EXIT", "VoiceSession", "read_voice_input", "record_voice", "speak"]
