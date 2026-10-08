import asyncio
import io
import struct
import threading
import wave
from types import SimpleNamespace

import pytest

from app.application.speech_service import SpeechService, decode_wav
from app.domain import AppError
from app.application import speech_service


def wav(seconds=1, channels=1, rate=16000, width=2):
    target = io.BytesIO()
    with wave.open(target, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(width)
        stream.setframerate(rate)
        stream.writeframes(b"\0" * int(seconds * rate * channels * width))
    return target.getvalue()


def settings(**overrides):
    values = dict(
        speech_key="test-only-key", speech_region="southeastasia", speech_language="vi-VN", speech_timeout=0.05
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def assert_error(call, code, status):
    with pytest.raises(AppError) as caught:
        call()
    assert caught.value.code == code
    assert caught.value.status == status
    return caught.value


@pytest.mark.parametrize("seconds", [1, 15])
def test_decode_pcm_and_duration(seconds):
    pcm, duration = decode_wav(wav(seconds))
    assert len(pcm) == seconds * 32000
    assert duration == seconds * 1000
    assert not pcm.startswith(b"RIFF")


@pytest.mark.parametrize(
    "blob,code,status",
    [
        (b"not audio", "AUDIO_TYPE_UNSUPPORTED", 415),
        (b"x" * (1048576 + 1), "AUDIO_TOO_LARGE", 413),
        (wav()[:-1], "AUDIO_INVALID", 422),
        (wav(0.9), "AUDIO_INVALID", 422),
        (wav(15.1), "AUDIO_INVALID", 422),
        (wav(channels=2), "AUDIO_TYPE_UNSUPPORTED", 415),
        (wav(rate=8000), "AUDIO_TYPE_UNSUPPORTED", 415),
        (wav(width=1), "AUDIO_TYPE_UNSUPPORTED", 415),
        (wav() + b"extra", "AUDIO_INVALID", 422),
    ],
    ids=["not-wav", "oversized", "truncated", "short", "long", "stereo", "rate", "width", "trailing"],
)
def test_invalid_audio_never_calls_provider(blob, code, status):
    calls = []
    service = SpeechService(settings(), provider=lambda *args: calls.append(args))
    assert_error(lambda: asyncio.run(service.transcribe(blob)), code, status)
    assert calls == []
    service.close()


def test_chunk_size_and_codec_validation():
    overflow = bytearray(wav())
    struct.pack_into("<I", overflow, 40, 999999)
    assert_error(lambda: decode_wav(bytes(overflow)), "AUDIO_INVALID", 422)
    float_pcm = bytearray(wav())
    struct.pack_into("<H", float_pcm, 20, 3)
    assert_error(lambda: decode_wav(bytes(float_pcm)), "AUDIO_TYPE_UNSUPPORTED", 415)


def test_recognized_transcript_and_timing():
    calls = []

    def provider(pcm, language):
        calls.append((pcm, language))
        return "  Tôi cần giày chạy bộ.  "

    service = SpeechService(settings(), provider=provider)
    result = asyncio.run(service.transcribe(wav()))
    assert result["transcript"] == "Tôi cần giày chạy bộ."
    assert result["language"] == "vi-VN"
    assert result["provider"] == "azure"
    assert result["audio_duration_ms"] == 1000
    assert set(result["timing_ms"]) == {"validation", "provider", "total"}
    assert len(calls[0][0]) == 32000
    service.close()


@pytest.mark.parametrize(
    "key,region,language",
    [("", "southeastasia", "vi-VN"), ("test-only", "eastus", "vi-VN"), ("test-only", "southeastasia", "en-US")],
)
def test_missing_or_unsupported_configuration(key, region, language):
    service = SpeechService(
        settings(speech_key=key, speech_region=region, speech_language=language), provider=lambda *_: "never"
    )
    assert not service.available
    assert service.configuration_state == "unconfigured"
    assert_error(lambda: asyncio.run(service.transcribe(wav())), "SPEECH_UNAVAILABLE", 503)
    service.close()


def test_language_and_empty_recognition():
    service = SpeechService(settings(), provider=lambda *_: "")
    assert service.configuration_state == "configured_unverified"
    assert_error(lambda: asyncio.run(service.transcribe(wav(), "en-US")), "VALIDATION_ERROR", 422)
    assert_error(lambda: asyncio.run(service.transcribe(wav())), "SPEECH_NO_MATCH", 422)
    service.close()


def test_timeout_keeps_slot_until_provider_finishes():
    entered, release = threading.Event(), threading.Event()
    calls = []

    def provider(*_):
        calls.append(1)
        entered.set()
        release.wait(2)
        return "Giày đen"

    service = SpeechService(settings(), provider=provider)

    async def exercise():
        with pytest.raises(AppError) as timeout:
            await service.transcribe(wav())
        assert timeout.value.code == "SPEECH_TIMEOUT"
        assert entered.is_set()
        with pytest.raises(AppError) as busy:
            await service.transcribe(wav())
        assert busy.value.code == "SPEECH_BUSY"
        assert len(calls) == 1
        release.set()
        for _ in range(100):
            await asyncio.sleep(0.002)
            if not service.busy:
                break
        assert (await service.transcribe(wav()))["transcript"] == "Giày đen"

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        service.close()


def test_unexpected_provider_failure_is_sanitized():
    def provider(*_):
        raise RuntimeError("SECRET raw provider exception")

    service = SpeechService(settings(), provider=provider)
    error = assert_error(lambda: asyncio.run(service.transcribe(wav())), "SPEECH_UPSTREAM_FAILED", 502)
    assert "SECRET" not in error.message
    service.close()


def fake_sdk(reason="recognized", text="Giày đen", error_code="ConnectionFailure"):
    calls = []
    reasons = SimpleNamespace(RecognizedSpeech="recognized", NoMatch="no_match", Canceled="canceled")
    codes = SimpleNamespace(
        AuthenticationFailure="AuthenticationFailure",
        Forbidden="Forbidden",
        TooManyRequests="TooManyRequests",
        ServiceTimeout="ServiceTimeout",
    )
    result = SimpleNamespace(
        reason=reason,
        text=text,
        cancellation_details=SimpleNamespace(error_code=error_code, error_details="SECRET do not expose"),
    )

    class Stream:
        def __init__(self, stream_format):
            calls.append(("stream_format", stream_format))

        def write(self, data):
            calls.append(("pcm", data))

        def close(self):
            calls.append(("close",))

    class Recognizer:
        def __init__(self, speech_config, audio_config):
            assert speech_config.speech_recognition_language == "vi-VN"

        def recognize_once_async(self):
            calls.append(("recognize",))
            return SimpleNamespace(get=lambda: result)

    sdk = SimpleNamespace(
        SpeechConfig=lambda **kwargs: SimpleNamespace(),
        SpeechRecognizer=Recognizer,
        ResultReason=reasons,
        CancellationErrorCode=codes,
        audio=SimpleNamespace(
            AudioStreamFormat=lambda **kwargs: kwargs, PushAudioInputStream=Stream, AudioConfig=lambda **kwargs: kwargs
        ),
    )
    return sdk, calls


def test_sdk_real_adapter_boundary_uses_pcm_and_single_call(monkeypatch):
    sdk, calls = fake_sdk()
    monkeypatch.setattr(speech_service, "_load_sdk", lambda: sdk)
    service = SpeechService(settings())
    assert calls == []  # Startup only imports; it never probes paid Azure.
    result = asyncio.run(service.transcribe(wav()))
    assert result["transcript"] == "Giày đen"
    assert len([call for call in calls if call[0] == "recognize"]) == 1
    assert [call[1] for call in calls if call[0] == "pcm"] == [b"\0" * 32000]
    assert ("stream_format", {"samples_per_second": 16000, "bits_per_sample": 16, "channels": 1}) in calls
    service.close()


@pytest.mark.parametrize(
    "reason,error_code,code,status",
    [
        ("no_match", "", "SPEECH_NO_MATCH", 422),
        ("canceled", "AuthenticationFailure", "SPEECH_AUTH_FAILED", 502),
        ("canceled", "Forbidden", "SPEECH_AUTH_FAILED", 502),
        ("canceled", "TooManyRequests", "SPEECH_RATE_LIMITED", 429),
        ("canceled", "ServiceTimeout", "SPEECH_TIMEOUT", 504),
        ("canceled", "ConnectionFailure", "SPEECH_UPSTREAM_FAILED", 502),
        ("canceled", "Unknown", "SPEECH_UPSTREAM_FAILED", 502),
        ("unknown_reason", "", "SPEECH_UPSTREAM_FAILED", 502),
    ],
)
def test_sdk_error_mapping(monkeypatch, reason, error_code, code, status):
    sdk, calls = fake_sdk(reason=reason, error_code=error_code)
    monkeypatch.setattr(speech_service, "_load_sdk", lambda: sdk)
    service = SpeechService(settings())
    error = assert_error(lambda: asyncio.run(service.transcribe(wav())), code, status)
    assert "SECRET" not in error.message
    assert not service.busy
    service.close()


def test_sdk_missing_is_safe_unavailable(monkeypatch):
    monkeypatch.setattr(speech_service, "_load_sdk", lambda: None)
    service = SpeechService(settings())
    assert not service.available
    assert service.configuration_state == "unconfigured"
    assert_error(lambda: asyncio.run(service.transcribe(wav())), "SPEECH_UNAVAILABLE", 503)
    service.close()


def test_request_cancel_keeps_native_busy():
    entered, release = threading.Event(), threading.Event()

    def provider(*_):
        entered.set()
        release.wait(2)
        return "Giày trắng"

    service = SpeechService(settings(speech_timeout=1), provider=provider)

    async def exercise():
        task = asyncio.create_task(service.transcribe(wav()))
        for _ in range(100):
            await asyncio.sleep(0.002)
            if entered.is_set():
                break
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert service.busy
        with pytest.raises(AppError) as busy:
            await service.transcribe(wav())
        assert busy.value.code == "SPEECH_BUSY"
        release.set()
        for _ in range(100):
            await asyncio.sleep(0.002)
            if not service.busy:
                break
        assert not service.busy

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        service.close()
