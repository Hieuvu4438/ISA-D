import asyncio
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.application.speech_service import SpeechService
from app.domain import AppError
from test_speech import settings, wav


def test_local_provider_needs_no_azure_key_or_budget(tmp_path, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Local speech must not reserve paid Azure calls")

    monkeypatch.setattr("app.data.speech_budget.SpeechBudget.reserve", forbidden)
    service = SpeechService(settings(root=tmp_path, speech_provider="local", speech_key=""),
                            provider=lambda *_: "Tôi cần một chiếc túi màu nâu")
    try:
        assert service.available
        assert service.provider == "local"
        result = asyncio.run(service.transcribe(wav()))
        assert result["provider"] == "local"
        assert result["transcript"] == "Tôi cần một chiếc túi màu nâu"
        assert not (tmp_path / "runtime" / "speech-live-budget.json").exists()
    finally:
        service.close()


def test_missing_local_model_is_unavailable_without_azure_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("app.application.speech_service._load_sdk", lambda: pytest.fail("Azure loaded"))
    service = SpeechService(settings(root=tmp_path, speech_provider="local"))
    try:
        assert not service.available
        with pytest.raises(AppError) as error:
            asyncio.run(service.transcribe(wav()))
        assert error.value.code == "SPEECH_UNAVAILABLE"
    finally:
        service.close()


def test_local_silence_is_rejected_before_model_inference():
    from app.application.local_speech import LocalSpeechRecognizer

    model = SimpleNamespace(transcribe=lambda *args, **kwargs: pytest.fail("Silence reached decoder"))
    recognizer = LocalSpeechRecognizer(model=model)
    with pytest.raises(AppError) as error:
        recognizer(b"\0" * 32000, "vi-VN")
    assert error.value.code == "SPEECH_NO_MATCH"


def test_local_decoder_uses_vietnamese_and_discards_no_speech():
    from app.application.local_speech import LocalSpeechRecognizer

    calls = []
    def transcribe(audio, **kwargs):
        calls.append((audio, kwargs))
        return iter([SimpleNamespace(text=" Xin chào", no_speech_prob=0.1, avg_logprob=-0.2),
                     SimpleNamespace(text=" hallucination", no_speech_prob=0.99, avg_logprob=-2)]), None

    recognizer = LocalSpeechRecognizer(model=SimpleNamespace(transcribe=transcribe))
    pcm = np.full(16000, 1000, dtype="<i2").tobytes()
    assert recognizer(pcm, "vi-VN") == "Xin chào"
    assert calls[0][0].dtype == np.float32
    assert calls[0][1]["language"] == "vi"
    assert calls[0][1]["beam_size"] == 5
    assert calls[0][1]["vad_filter"] is True


def test_local_model_load_is_cpu_only_and_cannot_download(tmp_path, monkeypatch):
    from app.application.local_speech import LocalSpeechRecognizer

    (tmp_path / "model.bin").write_bytes(b"fixture")
    calls = []
    def load(path, **kwargs):
        calls.append((path, kwargs))
        return SimpleNamespace()

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=load))
    LocalSpeechRecognizer(tmp_path)
    assert calls == [(str(tmp_path), {
        "device": "cpu", "compute_type": "int8", "cpu_threads": 4,
        "num_workers": 1, "local_files_only": True,
    })]


def test_empty_vad_result_is_no_match_without_azure_fallback(tmp_path):
    service = SpeechService(settings(root=tmp_path, speech_provider="local"), provider=lambda *_: "")
    try:
        with pytest.raises(AppError) as error:
            asyncio.run(service.transcribe(wav()))
        assert error.value.code == "SPEECH_NO_MATCH"
        assert not (tmp_path / "runtime" / "speech-live-budget.json").exists()
    finally:
        service.close()


def test_invalid_provider_does_not_use_azure(tmp_path, monkeypatch):
    monkeypatch.setattr("app.application.speech_service._load_sdk", lambda: pytest.fail("Azure loaded"))
    service = SpeechService(settings(root=tmp_path, speech_provider="invalid"))
    assert not service.available
    service.close()


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_model_path_environment_uses_provisioned_default(monkeypatch, value):
    from app.settings import Settings

    monkeypatch.setattr("app.settings.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("LOCAL_SPEECH_MODEL_PATH", value)
    monkeypatch.delenv("LOCAL_SPEECH_CPU_THREADS", raising=False)
    monkeypatch.delenv("LOCAL_SPEECH_TIMEOUT", raising=False)
    config = Settings.from_env()
    assert config.local_speech_model_path == config.root / "models" / "speech-whisper-small"


@pytest.mark.parametrize("values", [
    {"local_speech_cpu_threads": 0}, {"local_speech_cpu_threads": 17},
    {"local_speech_timeout": 0}, {"local_speech_timeout": 91},
    {"local_speech_timeout": float("nan")}, {"local_speech_timeout": float("inf")},
])
def test_local_resource_and_timeout_settings_are_bounded(values):
    from app.settings import Settings

    with pytest.raises(ValueError):
        Settings(**values)
