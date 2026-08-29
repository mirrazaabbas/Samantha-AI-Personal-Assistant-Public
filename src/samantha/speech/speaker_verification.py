"""Private on-device speaker enrollment and verification for Samantha."""

from __future__ import annotations

import io
import os
import subprocess
import time
import wave
from pathlib import Path

import numpy as np

from samantha.core.paths import get_config_dir

_MODEL_PATH = get_config_dir() / "models" / "voiceprint" / "wespeaker-resnet34.onnx"
_PROFILE_PATH = get_config_dir() / "voiceprint.npy"


class SpeakerVerifier:
    """Compare local speech embeddings against the enrolled owner's voice."""

    def __init__(
        self,
        model_path: Path = _MODEL_PATH,
        profile_path: Path = _PROFILE_PATH,
        *,
        threshold: float = 0.35,
    ) -> None:
        import onnxruntime as ort

        self.profile_path = profile_path
        self.threshold = threshold
        options = ort.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.profile = self._normalize(np.load(profile_path)).astype(np.float32)

    @staticmethod
    def is_enrolled(profile_path: Path = _PROFILE_PATH) -> bool:
        return profile_path.is_file()

    @staticmethod
    def _normalize(value: np.ndarray) -> np.ndarray:
        vector = np.asarray(value, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm <= 0:
            raise ValueError("Invalid zero-length speaker embedding")
        return vector / norm

    def embedding(self, audio: bytes) -> np.ndarray:
        import kaldi_native_fbank as knf

        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise ValueError("Speaker verification requires 16-bit mono WAV")
            sample_rate = wav_file.getframerate()
            samples = np.frombuffer(wav_file.readframes(wav_file.getnframes()), "<i2")
        if sample_rate != 16000 or samples.size < sample_rate // 2:
            raise ValueError("At least half a second of 16 kHz speech is required")

        options = knf.FbankOptions()
        options.frame_opts.samp_freq = float(sample_rate)
        options.frame_opts.frame_length_ms = 25.0
        options.frame_opts.frame_shift_ms = 10.0
        options.frame_opts.dither = 0.0
        options.frame_opts.window_type = "hamming"
        options.mel_opts.num_bins = 80
        fbank = knf.OnlineFbank(options)
        fbank.accept_waveform(sample_rate, samples.astype(np.float32).tolist())
        fbank.input_finished()
        features = np.asarray(
            [fbank.get_frame(index) for index in range(fbank.num_frames_ready)],
            dtype=np.float32,
        )
        if features.shape[0] < 20:
            raise ValueError("Not enough voiced audio for speaker verification")
        features -= features.mean(axis=0, keepdims=True)
        embedding = self.session.run(["embs"], {"feats": features[None, ...]})[0]
        return self._normalize(embedding)

    def score(self, audio: bytes) -> float:
        return float(np.dot(self.profile, self.embedding(audio)))

    def verify(
        self, audio: bytes, *, threshold: float | None = None
    ) -> tuple[bool, float]:
        try:
            score = self.score(audio)
        except Exception:
            return False, 0.0
        return score >= (self.threshold if threshold is None else threshold), score

    @classmethod
    def enroll(
        cls,
        samples: list[bytes],
        model_path: Path = _MODEL_PATH,
        profile_path: Path = _PROFILE_PATH,
    ) -> Path:
        # A temporary unit vector only initializes the model-backed extractor.
        # Publish the final profile atomically so failed enrollment stays locked.
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = profile_path.with_suffix(".enrolling.npy")
        placeholder = np.ones(256, dtype=np.float32)
        np.save(temporary_path, placeholder / np.linalg.norm(placeholder))
        try:
            verifier = cls(model_path, temporary_path)
            embeddings = [verifier.embedding(sample) for sample in samples]
            similarities = [
                (float(np.dot(embeddings[left], embeddings[right])), left, right)
                for left in range(len(embeddings))
                for right in range(left + 1, len(embeddings))
            ]
            if not similarities:
                raise ValueError("At least two enrollment samples are required")
            best_score, left, right = max(similarities)
            if best_score < 0.25:
                raise ValueError(
                    "Enrollment samples did not match consistently "
                    f"(best voice score={best_score:.3f})"
                )
            # A cough, room sound, or clipped recording should not poison the
            # owner profile. Build it from the two most consistent samples.
            profile = verifier._normalize(
                np.mean([embeddings[left], embeddings[right]], axis=0)
            )
            np.save(temporary_path, profile.astype(np.float32))
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, profile_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        return profile_path


def enroll_interactively() -> Path:
    """Capture three local owner samples and save only their mean embedding."""
    from samantha.speech.macos_tts import MacOSTTSBackend
    from samantha.speech.voice_io import play_wav, record_until_silence

    service = f"gui/{os.getuid()}/com.samantha.samantha-voice"
    plist = Path.home() / "Library/LaunchAgents/com.samantha.samantha-voice.plist"
    subprocess.run(
        ["/bin/launchctl", "bootout", service],
        check=False,
        capture_output=True,
    )
    time.sleep(1.0)
    try:
        phrase = "Hi Samantha, verify my private voice and follow only my commands."
        phrases = [phrase, phrase, phrase]
        samples: list[bytes] = []
        voice = MacOSTTSBackend()
        for index, phrase in enumerate(phrases, 1):
            prompt = voice.synthesize(
                f"Voice enrollment sample {index}. After the tone, say: {phrase}",
                voice_id="",
                output_format="wav",
            )
            play_wav(prompt.audio, sample_rate=prompt.sample_rate)
            samples.append(
                record_until_silence(
                    silence_threshold=350,
                    silence_seconds=0.7,
                    startup_silence_seconds=8.0,
                    max_seconds=12.0,
                    keep_waiting_on_silence=False,
                )
            )
        path = SpeakerVerifier.enroll(samples)
        done = voice.synthesize(
            "Your private voiceprint is enrolled, Sir.",
            voice_id="",
            output_format="wav",
        )
        play_wav(done.audio, sample_rate=done.sample_rate)
        return path
    finally:
        subprocess.run(
            ["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            ["/bin/launchctl", "kickstart", "-k", service],
            check=False,
            capture_output=True,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "enroll":
        print(enroll_interactively())
    else:
        raise SystemExit("Usage: python -m samantha.speech.speaker_verification enroll")
