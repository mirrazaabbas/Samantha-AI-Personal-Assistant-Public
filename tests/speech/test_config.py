"""Tests for speech configuration."""

from samantha.core.config import SamanthaConfig, SpeechConfig


def test_speech_config_defaults():
    cfg = SpeechConfig()
    assert cfg.backend == "auto"
    assert cfg.model == "base"
    assert cfg.language == ""
    assert cfg.device == "auto"
    assert cfg.compute_type == "float16"


def test_samantha_config_has_speech():
    cfg = SamanthaConfig()
    assert hasattr(cfg, "speech")
    assert isinstance(cfg.speech, SpeechConfig)
    assert cfg.speech.backend == "auto"


def test_samantha_system_has_speech_backend():
    """SamanthaSystem has a speech_backend attribute."""
    from samantha.system import SamanthaSystem

    assert "speech_backend" in SamanthaSystem.__dataclass_fields__
