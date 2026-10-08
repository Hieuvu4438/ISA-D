"""Bounded speech adapters. Audio is validated and kept only in memory."""

import asyncio
import importlib
import re
import struct
import threading
import time
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.domain import AppError
from app.data.speech_budget import SpeechBudget
from app.application.local_speech import LocalSpeechRecognizer
from app.application.groq_speech import GroqSpeechRecognizer


def decode_wav(blob: bytes) -> tuple[bytes, int]:
    """Return raw PCM and duration; distrust every declared RIFF/chunk size."""
    if len(blob) > 1048576:
        raise AppError(413, "AUDIO_TOO_LARGE", "Âm thanh vượt quá 1 MiB.", "audio")
    if len(blob) < 12 or blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        raise AppError(415, "AUDIO_TYPE_UNSUPPORTED", "Chỉ hỗ trợ WAV PCM16 mono 16 kHz.", "audio")

    def invalid():
        return AppError(422, "AUDIO_INVALID", "Tệp WAV không hợp lệ hoặc thời lượng ngoài 1–15 giây.", "audio")

    if struct.unpack_from("<I", blob, 4)[0] + 8 != len(blob):
        raise invalid()
    position, fmt, pcm = 12, None, None
    while position < len(blob):
        if position + 8 > len(blob):
            raise invalid()
        chunk, size = struct.unpack_from("<4sI", blob, position)
        position += 8
        end = position + size
        if end > len(blob) or end + (size % 2) > len(blob):
            raise invalid()
        if chunk == b"fmt ":
            if fmt is not None or size < 16:
                raise invalid()
            fmt = struct.unpack_from("<HHIIHH", blob, position)
        elif chunk == b"data":
            if pcm is not None or fmt is None:
                raise invalid()
            pcm = blob[position:end]
        position = end + size % 2
    if fmt is None or pcm is None:
        raise invalid()
    codec, channels, rate, byte_rate, align, bits = fmt
    if (codec, channels, rate, bits) != (1, 1, 16000, 16):
        raise AppError(415, "AUDIO_TYPE_UNSUPPORTED", "Chỉ hỗ trợ WAV PCM16 mono 16 kHz.", "audio")
    if (byte_rate, align) != (32000, 2) or len(pcm) % 2 or not 32000 <= len(pcm) <= 480000:
        raise invalid()
    return pcm, round(len(pcm) / 32)


def _load_sdk():
    try:
        return importlib.import_module("azure.cognitiveservices.speech")
    except (ImportError, OSError):
        return None


class SpeechService:
    def __init__(self, settings, provider=None):
        self._key = settings.speech_key
        self._region = settings.speech_region
        self._language = settings.speech_language
        self._timeout = settings.speech_timeout
        self.provider = getattr(settings, "speech_provider", "azure")
        self._sdk = None
        self._provider = provider
        if self.provider == "local":
            self._timeout = getattr(settings, "local_speech_timeout", 90.0)
            if provider is None:
                path = getattr(settings, "local_speech_model_path", None)
                path = path or Path(getattr(settings, "root", ".")) / "models" / "speech-whisper-small"
                try:
                    self._provider = LocalSpeechRecognizer(
                        path, cpu_threads=getattr(settings, "local_speech_cpu_threads", 4)
                    )
                except Exception:
                    self._provider = None
            self.available = self._provider is not None and self._language == "vi-VN"
        elif self.provider == "groq":
            self._timeout = getattr(settings, "groq_speech_timeout", 30.0)
            groq_key = getattr(settings, "groq_api_key", "").strip()
            groq_model = getattr(settings, "groq_speech_model", "whisper-large-v3")
            if provider is None:
                self._provider = GroqSpeechRecognizer(groq_key, model=groq_model, timeout=self._timeout)
            self.available = bool(groq_key and self._language == "vi-VN")
        elif self.provider == "azure":
            self._sdk = None if provider is not None else _load_sdk()
            valid_key = isinstance(self._key, str) and bool(self._key.strip()) and not re.search(r"\s", self._key)
            self.available = bool(
                valid_key and self._region == "southeastasia" and self._language == "vi-VN"
                and (provider is not None or self._sdk is not None)
            )
            self._provider = provider or self._recognize_azure
        else:
            self.available = False
        self.configuration_state = "configured_unverified" if self.available else "unconfigured"
        self._budget = SpeechBudget(getattr(settings, "root", None)) if self.provider == "azure" else None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demo-speech")
        self._lock = threading.Lock()
        self._busy = False

    @property
    def busy(self):
        with self._lock:
            return self._busy

    def _release(self, _future):
        with self._lock:
            self._busy = False

    def close(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def transcribe(self, audio_bytes: bytes, language="vi-VN") -> dict:
        started = time.perf_counter()
        if language != "vi-VN":
            raise AppError(422, "VALIDATION_ERROR", "Ngôn ngữ phải là vi-VN.", "language")
        pcm, duration_ms = decode_wav(audio_bytes)
        validation_ms = (time.perf_counter() - started) * 1000
        if not self.available:
            raise AppError(503, "SPEECH_UNAVAILABLE", "Dịch vụ nhận dạng chưa được cấu hình hoặc model không khả dụng.")
        with self._lock:
            if self._busy:
                raise AppError(429, "SPEECH_BUSY", "Nhận dạng đang bận. Vui lòng thử lại sau.", retryable=True)
            self._busy = True
        provider_start = time.perf_counter()
        try:
            native = self._executor.submit(self._run_provider, audio_bytes, pcm, language, duration_ms)
        except Exception:
            self._release(None)
            raise AppError(503, "SPEECH_UNAVAILABLE", "Dịch vụ nhận dạng chưa sẵn sàng.") from None
        native.add_done_callback(self._release)
        future = asyncio.wrap_future(native)
        # A timed-out or disconnected HTTP request must not free a native slot.
        # Consume late exceptions without logging provider payloads.
        future.add_done_callback(lambda finished: finished.exception() if not finished.cancelled() else None)
        try:
            transcript = await asyncio.wait_for(asyncio.shield(future), timeout=self._timeout)
        except asyncio.TimeoutError:
            raise AppError(
                504, "SPEECH_TIMEOUT", "Nhận dạng quá thời gian. Vui lòng thử lại.", retryable=True
            ) from None
        except AppError:
            raise
        except Exception:
            raise AppError(
                502, "SPEECH_UPSTREAM_FAILED", "Dịch vụ nhận dạng gặp lỗi. Vui lòng thử lại.", retryable=True
            ) from None
        if not isinstance(transcript, str) or not transcript.strip():
            raise AppError(422, "SPEECH_NO_MATCH", "Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.", "audio")
        transcript = " ".join(unicodedata.normalize("NFC", transcript).split())
        ended = time.perf_counter()
        return {
            "transcript": transcript,
            "language": language,
            "provider": self.provider,
            "audio_duration_ms": duration_ms,
            "timing_ms": {
                "validation": round(validation_ms, 3),
                "provider": round((ended - provider_start) * 1000, 3),
                "total": round((ended - started) * 1000, 3),
            },
        }

    def _run_provider(self, audio, pcm, language, duration_ms):
        if self.provider == "local":
            return self._provider(pcm, language)
        if self.provider == "groq":
            return self._provider(pcm, language, audio_bytes=audio)
        attempt = self._budget.reserve(audio, duration_ms)
        try:
            transcript = self._provider(pcm, language)
        except AppError as error:
            self._budget.finish(attempt, error.code)
            raise
        except Exception:
            self._budget.finish(attempt, "SPEECH_UPSTREAM_FAILED")
            raise
        self._budget.finish(attempt, "recognized" if isinstance(transcript, str) and transcript.strip()
                            else "SPEECH_NO_MATCH")
        return transcript

    def _recognize_azure(self, pcm, language):
        sdk = self._sdk
        config = sdk.SpeechConfig(subscription=self._key, region=self._region)
        config.speech_recognition_language = language
        stream = sdk.audio.PushAudioInputStream(
            stream_format=sdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        )
        stream_closed = False
        try:
            recognizer = sdk.SpeechRecognizer(speech_config=config, audio_config=sdk.audio.AudioConfig(stream=stream))
            recognition = recognizer.recognize_once_async()
            stream.write(pcm)
            stream.close()
            stream_closed = True
            result = recognition.get()
            if result.reason == sdk.ResultReason.RecognizedSpeech:
                return result.text
            if result.reason == sdk.ResultReason.NoMatch:
                raise AppError(422, "SPEECH_NO_MATCH", "Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.", "audio")
            if result.reason == sdk.ResultReason.Canceled:
                code = result.cancellation_details.error_code
                codes = sdk.CancellationErrorCode
                if code in (codes.AuthenticationFailure, codes.Forbidden):
                    raise AppError(502, "SPEECH_AUTH_FAILED", "Cấu hình Azure Speech không được chấp nhận.")
                if code == codes.TooManyRequests:
                    raise AppError(429, "SPEECH_RATE_LIMITED", "Azure Speech đang giới hạn lượt gọi.", retryable=True)
                if code == codes.ServiceTimeout:
                    raise AppError(504, "SPEECH_TIMEOUT", "Nhận dạng quá thời gian. Vui lòng thử lại.", retryable=True)
            raise AppError(
                502, "SPEECH_UPSTREAM_FAILED", "Dịch vụ nhận dạng gặp lỗi. Vui lòng thử lại.", retryable=True
            )
        finally:
            if not stream_closed:
                stream.close()
