"""Always-on, local wake-phrase listener for Samantha on macOS."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from samantha.cli._fast_voice_commands import handle_fast_voice_command
from samantha.cli._voice_chat import VoiceSession
from samantha.core.config import load_config
from samantha.speech.macos_tts import MacOSTTSBackend
from samantha.speech.speaker_verification import SpeakerVerifier
from samantha.speech.voice_io import (
    play_wav,
    play_wav_interruptible,
    record_until_silence,
)

logger = logging.getLogger(__name__)
_WAKE_RE = re.compile(
    r"\b(?:hi|high|hey|hello)[\s,.:;!?-]+"
    r"(?:samantha|samanta|samanth|sam\s+antha)\b",
    re.IGNORECASE,
)
_RUNNING = True
_ACTIVITY_LOG = Path.home() / ".samantha" / "samantha-activity.jsonl"
_SENSITIVE_COMMAND = re.compile(
    r"\b(?:delete|remove|erase|send|email|message|post|publish|buy|purchase|"
    r"pay|transfer|install|uninstall|shutdown|restart|run\s+(?:a\s+)?shell|"
    r"change\s+(?:a\s+)?password)\b",
    re.IGNORECASE,
)
_CONFIRM_WORDS = {"yes", "confirm", "confirmed", "proceed", "do it", "continue"}


def _record_activity(event: str, *, command: str = "", detail: str = "") -> None:
    """Append a private, content-minimized activity event for troubleshooting."""
    _ACTIVITY_LOG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event,
        "command_id": (
            hashlib.sha256(command.casefold().encode()).hexdigest()[:12]
            if command
            else ""
        ),
        "detail": detail[:200],
    }
    fd = os.open(_ACTIVITY_LOG, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _requires_confirmation(command: str) -> bool:
    """Return whether a voice command can cause sensitive external changes."""
    return _SENSITIVE_COMMAND.search(command) is not None


def _is_confirmation(command: str) -> bool:
    normalized = re.sub(r"[^a-z ]+", "", command.casefold()).strip()
    return normalized in _CONFIRM_WORDS


def _stop(*_: Any) -> None:
    global _RUNNING
    _RUNNING = False


def _transcribe(
    session: VoiceSession,
    *,
    wait: bool,
    verifier: SpeakerVerifier,
) -> str:
    backend = session.get_stt_backend()
    if backend is None:
        raise RuntimeError("No local speech-to-text backend is available")
    audio = record_until_silence(
        keep_waiting_on_silence=wait,
        silence_threshold=350,
        silence_seconds=0.65,
        startup_silence_seconds=4.0,
        max_seconds=12.0,
    )
    if len(audio) <= 64:
        return ""
    verified, score = verifier.verify(audio)
    if not verified:
        logger.warning("Ignored unrecognized speaker (score=%.3f)", score)
        return ""
    logger.info("Owner voice verified (score=%.3f)", score)
    result = backend.transcribe(audio, format="wav", language="en")
    return result.text.strip()


def _clean_command(text: str) -> str:
    """Remove common conversational filler and duplicated STT phrases."""
    cleaned = re.sub(
        r"^\s*(?:okay|ok|alright|right)[,\s]+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,.!?")
    parts = [part.strip(" ,.!?") for part in cleaned.split(",") if part.strip()]
    if len(parts) >= 2 and parts[0].casefold() == parts[1].casefold():
        return parts[0]
    return cleaned


def _speak(
    text: str,
    *,
    voice: str,
    session: VoiceSession | None = None,
    verifier: SpeakerVerifier | None = None,
    interruptible: bool = False,
) -> str:
    try:
        result = MacOSTTSBackend().synthesize(
            text,
            voice_id=voice,
            output_format="wav",
        )
    except (OSError, RuntimeError) as exc:
        # Audio devices can temporarily disappear during login, sleep/wake,
        # or permission changes. Keep the always-on listener alive so it can
        # recover as soon as macOS makes the output device available again.
        logger.warning("Speech output temporarily unavailable: %s", exc)
        return ""
    if not interruptible or session is None or verifier is None:
        play_wav(result.audio, sample_rate=result.sample_rate)
        return ""
    captured = play_wav_interruptible(
        result.audio,
        duration_seconds=max(0.5, result.duration_seconds),
    )
    if not captured:
        return ""
    # Interruptions are often a single short word ("stop"), so use a slightly
    # lower owner-match threshold while still requiring biometric similarity.
    verified, score = verifier.verify(captured, threshold=0.25)
    if not verified:
        logger.warning("Ignored interruption from unrecognized speaker (%.3f)", score)
        return ""
    backend = session.get_stt_backend()
    if backend is None:
        return ""
    transcription = backend.transcribe(captured, format="wav", language="en")
    interruption = _clean_command(transcription.text)
    logger.info("Owner interrupted current speech")
    return interruption


def _is_stop_command(command: str) -> bool:
    normalized = re.sub(r"[^a-z ]+", "", command.casefold()).strip()
    return normalized in {
        "stop",
        "samantha stop",
        "stop samantha",
        "cancel",
        "be quiet",
        "silence",
    }


def _server_healthy(server_url: str) -> bool:
    try:
        with urlopen(f"{server_url}/health", timeout=2):  # noqa: S310
            return True
    except (OSError, URLError):
        return False


def _ensure_server(samantha: Path, server_url: str) -> bool:
    if _server_healthy(server_url):
        return True
    try:
        subprocess.run([str(samantha), "start"], check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    for delay in (0.25, 0.5, 1.0, 2.0):
        if _server_healthy(server_url):
            return True
        time.sleep(delay)
    return False


def _ask_server(
    command: str,
    server_url: str,
    *,
    model: str = "qwen3:1.7b",
    samantha: Path | None = None,
    attempts: int = 2,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": command}],
            "max_tokens": 220,
            "temperature": 0.2,
        }
    ).encode()
    request = Request(  # noqa: S310
        f"{server_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            with urlopen(request, timeout=90) as response:  # noqa: S310
                data = json.loads(response.read())
            text = str(data["choices"][0]["message"]["content"]).strip()
            if not text:
                raise RuntimeError("The assistant returned an empty response")
            return text
        except (OSError, URLError, KeyError, ValueError, RuntimeError) as exc:
            error = exc
            if attempt + 1 < attempts:
                if samantha is not None:
                    _ensure_server(samantha, server_url)
                time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(f"Assistant server did not respond: {error}") from error


def _startup_health(
    session: VoiceSession, samantha: Path, server_url: str
) -> dict[str, bool]:
    """Check the complete local voice path without recording or speaking."""

    def safe(check: Any) -> bool:
        try:
            return bool(check())
        except Exception:
            logger.exception("Startup health check failed")
            return False

    def microphone_available() -> bool:
        import sounddevice as sd

        default_input = sd.query_devices(kind="input")
        return int(default_input.get("max_input_channels", 0)) > 0

    def model_available() -> bool:
        with urlopen(f"{server_url}/v1/models", timeout=3) as response:  # noqa: S310
            payload = json.loads(response.read())
        return bool(payload.get("data"))

    def internet_reachable() -> bool:
        result = subprocess.run(
            ["/usr/sbin/scutil", "-r", "www.apple.com"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0 and "Not Reachable" not in result.stdout

    root = samantha.parents[2]
    checks = {
        "voiceprint": SpeakerVerifier.is_enrolled(),
        "microphone": safe(microphone_available),
        "speech_recognition": safe(lambda: session.get_stt_backend() is not None),
        "speech_output": MacOSTTSBackend().health(),
        "assistant_server": _ensure_server(samantha, server_url),
        "model": safe(model_available),
        "internet": safe(internet_reachable),
        "automations": (root / "src/samantha/operators/data").is_dir(),
        "private_logging": safe(
            lambda: (
                _ACTIVITY_LOG.parent.exists()
                and os.access(_ACTIVITY_LOG.parent, os.W_OK)
            )
        ),
    }
    _record_activity(
        "startup_health",
        detail=",".join(
            f"{name}={'ok' if ok else 'failed'}" for name, ok in checks.items()
        ),
    )
    return checks


def run() -> None:
    """Listen forever, handling one command after each local wake phrase."""
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    root = Path(__file__).resolve().parents[3]
    samantha = root / ".venv" / "bin" / "samantha"
    server_url = "http://127.0.0.1:8000"
    # Follow the voice selected in macOS Read & Speak. Apple may substitute an
    # API-available voice when a private Siri-only voice cannot be used by say.
    voice = ""
    session = VoiceSession()
    model = load_config().intelligence.default_model or "qwen3:1.7b"
    health = _startup_health(session, samantha, server_url)
    failed = [name.replace("_", " ") for name, ok in health.items() if not ok]
    if failed and health["speech_output"]:
        _speak(
            "Samantha startup check found a problem with " + ", ".join(failed) + ".",
            voice=voice,
        )
    if not SpeakerVerifier.is_enrolled():
        logger.error("No owner voiceprint enrolled; voice commands are locked")
    while _RUNNING and not SpeakerVerifier.is_enrolled():
        time.sleep(5)
    if not _RUNNING:
        return
    verifier = SpeakerVerifier()
    logger.info("Samantha voice listener ready; wake phrase: Hi Samantha")

    while _RUNNING:
        try:
            heard = _transcribe(session, wait=True, verifier=verifier)
            if heard:
                logger.info("Verified speech received")
            wake = _WAKE_RE.search(heard)
            if wake is None:
                continue
            command = _clean_command(heard[wake.end() :])
            _record_activity("wake_verified")
            _speak("Yes, Sir.", voice=voice)
            if not command:
                command = _clean_command(
                    _transcribe(session, wait=False, verifier=verifier)
                )
            if not command:
                _speak("I did not hear a command, Sir.", voice=voice)
                _record_activity("command_missing")
                continue
            command_id = hashlib.sha256(command.casefold().encode()).hexdigest()[:12]
            logger.info("Command recognized (id=%s)", command_id)
            _record_activity("command_received", command=command)
            while command:
                if _is_stop_command(command):
                    _speak("Stopped, Sir.", voice=voice)
                    _record_activity("command_stopped", command=command)
                    break
                if _requires_confirmation(command):
                    _speak(
                        "This command may change data or contact another service. "
                        "Say confirm to continue, Sir.",
                        voice=voice,
                    )
                    confirmation = _clean_command(
                        _transcribe(session, wait=False, verifier=verifier)
                    )
                    if not _is_confirmation(confirmation):
                        _speak("Cancelled, Sir.", voice=voice)
                        _record_activity("confirmation_denied", command=command)
                        break
                    _record_activity("confirmation_approved", command=command)
                response = handle_fast_voice_command(command)
                if response is None:
                    response = _ask_server(
                        command,
                        server_url,
                        model=model,
                        samantha=samantha,
                    )
                _record_activity("command_completed", command=command)
                command = _speak(
                    response,
                    voice=voice,
                    session=session,
                    verifier=verifier,
                    interruptible=True,
                )
        except Exception as exc:
            logger.exception("Voice listener cycle failed")
            _record_activity("command_failed", detail=type(exc).__name__)
            try:
                _speak(
                    "I could not complete that command. I have logged the problem "
                    "and will keep listening, Sir.",
                    voice=voice,
                )
            except Exception:
                logger.exception("Could not speak failure notification")
            time.sleep(2)


if __name__ == "__main__":
    run()
