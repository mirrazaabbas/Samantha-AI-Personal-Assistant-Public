from unittest.mock import MagicMock, patch
from urllib.error import URLError

from samantha.speech.voice_daemon import (
    _WAKE_RE,
    _ask_server,
    _clean_command,
    _ensure_server,
    _is_confirmation,
    _is_stop_command,
    _record_activity,
    _requires_confirmation,
    _speak,
    _startup_health,
)


def test_hi_samantha_wake_phrase_and_inline_command():
    heard = "Hi Samantha list my priorities"
    match = _WAKE_RE.search(heard)
    assert match is not None
    assert heard[match.end() :].strip() == "list my priorities"


def test_common_name_variants_wake_samantha():
    assert _WAKE_RE.search("Hey Samanta")
    assert _WAKE_RE.search("hello Samanth")
    assert _WAKE_RE.search("Hi, Samantha.")
    assert _WAKE_RE.search("High Sam Antha")


def test_clean_command_removes_filler_and_duplicate_transcription():
    assert (
        _clean_command("Okay, open the google chrome, open the google chrome,")
        == "open the google chrome"
    )


def test_stop_command_variants():
    assert _is_stop_command("stop")
    assert _is_stop_command("Samantha, stop!")
    assert _is_stop_command("stop Samantha")
    assert not _is_stop_command("stopwatch")


def test_sensitive_commands_require_voice_confirmation():
    assert _requires_confirmation("send this email to the team")
    assert _requires_confirmation("delete the old document")
    assert _requires_confirmation("buy the selected product")
    assert not _requires_confirmation("open Excel")
    assert not _requires_confirmation("list my priorities")
    assert _is_confirmation("Yes!")
    assert _is_confirmation("do it")
    assert not _is_confirmation("maybe later")


def test_activity_log_is_private_and_does_not_store_command(tmp_path):
    path = tmp_path / "activity.jsonl"
    with patch("samantha.speech.voice_daemon._ACTIVITY_LOG", path):
        _record_activity("command_received", command="private secret command")
    data = path.read_text()
    assert "private secret command" not in data
    assert "command_received" in data
    assert path.stat().st_mode & 0o777 == 0o600


def test_startup_health_reports_failures_without_crashing(tmp_path):
    samantha = tmp_path / ".venv" / "bin" / "samantha"
    session = MagicMock()
    session.get_stt_backend.side_effect = RuntimeError("model unavailable")
    with (
        patch(
            "samantha.speech.voice_daemon.SpeakerVerifier.is_enrolled",
            return_value=True,
        ),
        patch("samantha.speech.voice_daemon._ensure_server", return_value=False),
        patch("samantha.speech.voice_daemon._record_activity"),
        patch(
            "samantha.speech.voice_daemon.MacOSTTSBackend.health",
            return_value=True,
        ),
    ):
        checks = _startup_health(session, samantha, "http://127.0.0.1:8000")
    assert checks["voiceprint"]
    assert checks["speech_output"]
    assert not checks["speech_recognition"]
    assert not checks["assistant_server"]


def test_speak_keeps_listener_alive_when_audio_is_unavailable():
    with patch(
        "samantha.speech.voice_daemon.MacOSTTSBackend.synthesize",
        side_effect=RuntimeError("no output device"),
    ):
        assert _speak("Still listening", voice="") == ""


def test_ensure_server_does_not_restart_healthy_server(tmp_path):
    response = MagicMock()
    response.__enter__.return_value = response
    with (
        patch("samantha.speech.voice_daemon.urlopen", return_value=response),
        patch("samantha.speech.voice_daemon.subprocess.run") as run,
    ):
        _ensure_server(tmp_path / "samantha", "http://127.0.0.1:8000")
    run.assert_not_called()


def test_ensure_server_restarts_and_waits_until_healthy(tmp_path):
    with (
        patch(
            "samantha.speech.voice_daemon._server_healthy",
            side_effect=[False, False, True],
        ),
        patch("samantha.speech.voice_daemon.subprocess.run") as run,
        patch("samantha.speech.voice_daemon.time.sleep"),
    ):
        assert _ensure_server(tmp_path / "samantha", "http://127.0.0.1:8000")
    run.assert_called_once()


def test_ask_server_returns_assistant_text():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'{"choices":[{"message":{"content":"Ready, Sir."}}]}'
    with patch("samantha.speech.voice_daemon.urlopen", return_value=response):
        assert _ask_server("status", "http://127.0.0.1:8000") == "Ready, Sir."


def test_ask_server_retries_transient_failure():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'{"choices":[{"message":{"content":"Recovered"}}]}'
    with (
        patch(
            "samantha.speech.voice_daemon.urlopen",
            side_effect=[URLError("offline"), response],
        ),
        patch("samantha.speech.voice_daemon.time.sleep"),
    ):
        assert _ask_server("status", "http://127.0.0.1:8000") == "Recovered"
