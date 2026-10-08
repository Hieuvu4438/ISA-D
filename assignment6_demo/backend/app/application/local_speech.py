"""Offline Vietnamese recognition with a pre-provisioned CTranslate2 Whisper model."""

from pathlib import Path

import numpy as np

from app.domain import AppError


class LocalSpeechRecognizer:
    def __init__(self, model_path=None, cpu_threads=4, *, model=None):
        if model is None:
            model_path = Path(model_path)
            if not (model_path / "model.bin").is_file():
                raise FileNotFoundError("Local speech model has not been provisioned")
            from faster_whisper import WhisperModel

            model = WhisperModel(str(model_path), device="cpu", compute_type="int8",
                                 cpu_threads=cpu_threads, num_workers=1, local_files_only=True)
        self._model = model

    def __call__(self, pcm, language):
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        # Reject digital silence and near-zero capture before Whisper's decoder can hallucinate.
        if not samples.size or np.sqrt(np.mean(samples * samples)) < 0.0001:
            raise AppError(422, "SPEECH_NO_MATCH", "Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.", "audio")
        segments, _ = self._model.transcribe(
            samples, language="vi", task="transcribe", beam_size=5, vad_filter=True,
            condition_on_previous_text=False, temperature=0.0,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        accepted = []
        for segment in segments:
            if segment.no_speech_prob > 0.6 and segment.avg_logprob < -1.0:
                continue
            if segment.text.strip():
                accepted.append(segment.text.strip())
        return " ".join(accepted)
