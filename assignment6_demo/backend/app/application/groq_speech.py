"""Groq Cloud Whisper API speech adapter for fast and accurate Vietnamese recognition."""

from __future__ import annotations

import io
import struct
import requests

from app.domain import AppError

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def _pcm_to_wav(pcm: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Encode raw PCM16 bytes into valid in-memory WAV container."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = len(pcm)
    riff_chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm


class GroqSpeechRecognizer:
    def __init__(self, api_key: str, model: str = "whisper-large-v3", timeout: float = 30.0):
        self._api_key = api_key.strip() if api_key else ""
        self._model = model.strip() if model else "whisper-large-v3"
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def __call__(self, pcm: bytes, language: str = "vi-VN", audio_bytes: bytes | None = None) -> str:
        if not self._api_key:
            raise AppError(502, "SPEECH_AUTH_FAILED", "Chưa cấu hình GROQ_API_KEY.")

        wav_payload = audio_bytes if (audio_bytes and audio_bytes[:4] == b"RIFF") else _pcm_to_wav(pcm)
        iso_language = "vi" if language in ("vi-VN", "vi", "vie") else language

        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        files = {
            "file": ("audio.wav", io.BytesIO(wav_payload), "audio/wav"),
        }
        data = {
            "model": self._model,
            "language": iso_language,
            "temperature": "0",
            "response_format": "json",
        }

        try:
            response = requests.post(
                GROQ_TRANSCRIPTION_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=self._timeout,
            )
        except requests.Timeout:
            raise AppError(504, "SPEECH_TIMEOUT", "Nhận dạng quá thời gian. Vui lòng thử lại.", retryable=True) from None
        except requests.RequestException:
            raise AppError(502, "SPEECH_UPSTREAM_FAILED", "Không thể kết nối tới dịch vụ Groq.", retryable=True) from None

        if response.status_code == 200:
            try:
                payload = response.json()
                transcript = payload.get("text", "")
                if not transcript or not transcript.strip():
                    raise AppError(422, "SPEECH_NO_MATCH", "Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.", "audio")
                return transcript.strip()
            except ValueError:
                raise AppError(502, "SPEECH_UPSTREAM_FAILED", "Dữ liệu trả về từ Groq không hợp lệ.", retryable=True)

        if response.status_code == 401:
            raise AppError(502, "SPEECH_AUTH_FAILED", "Khóa xác thực GROQ_API_KEY không được chấp nhận.")
        if response.status_code == 429:
            raise AppError(429, "SPEECH_RATE_LIMITED", "Groq API đang giới hạn tần suất gọi.", retryable=True)
        if response.status_code == 400:
            raise AppError(422, "SPEECH_NO_MATCH", "Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.", "audio")
        
        raise AppError(502, "SPEECH_UPSTREAM_FAILED", f"Groq API trả về mã lỗi HTTP {response.status_code}.", retryable=True)
