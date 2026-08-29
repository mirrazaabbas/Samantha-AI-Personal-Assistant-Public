from pathlib import Path

import numpy as np
import pytest

from samantha.speech.speaker_verification import SpeakerVerifier


def test_normalize_returns_unit_vector():
    result = SpeakerVerifier._normalize(np.asarray([3.0, 4.0], dtype=np.float32))
    assert np.linalg.norm(result) == pytest.approx(1.0)


def test_normalize_rejects_zero_vector():
    with pytest.raises(ValueError, match="zero-length"):
        SpeakerVerifier._normalize(np.zeros(3, dtype=np.float32))


def test_is_enrolled_uses_local_profile(tmp_path: Path):
    profile = tmp_path / "voiceprint.npy"
    assert not SpeakerVerifier.is_enrolled(profile)
    np.save(profile, np.ones(2, dtype=np.float32))
    assert SpeakerVerifier.is_enrolled(profile)
