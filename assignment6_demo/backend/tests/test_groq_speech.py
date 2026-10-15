"""Unit tests for Groq Cloud Whisper speech adapter."""

import pytest
from unittest.mock import patch, MagicMock

from app.domain import AppError
from app.application.groq_speech import GroqSpeechRecognizer, _pcm_to_wav


def test_pcm_to_wav_header():
    dummy_pcm = b"\x00\x00" * 16000  # 1 second of 16kHz mono 16-bit
    wav = _pcm_to_wav(dummy_pcm)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "
    assert len(wav) == 44 + len(dummy_pcm)


def test_groq_recognizer_unconfigured():
    recognizer = GroqSpeechRecognizer("")
    assert not recognizer.available
    with pytest.raises(AppError) as exc_info:
        recognizer(b"\x00" * 32000, "vi-VN")
    assert exc_info.value.code == "SPEECH_AUTH_FAILED"


@patch("requests.post")
def test_groq_recognizer_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "áo khoác denim màu xanh"}
    mock_post.return_value = mock_response

    recognizer = GroqSpeechRecognizer("test-key", model="whisper-large-v3")
    assert recognizer.available

    text = recognizer(b"\x00" * 32000, "vi-VN")
    assert text == "áo khoác denim màu xanh"
    mock_post.assert_called_once()
    assert "https://api.groq.com" in mock_post.call_args[0][0]


@patch("requests.post")
def test_groq_recognizer_auth_failure(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response

    recognizer = GroqSpeechRecognizer("invalid-key")
    with pytest.raises(AppError) as exc_info:
        recognizer(b"\x00" * 32000, "vi-VN")
    assert exc_info.value.code == "SPEECH_AUTH_FAILED"


@patch("requests.post")
def test_groq_recognizer_rate_limit(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_post.return_value = mock_response

    recognizer = GroqSpeechRecognizer("valid-key")
    with pytest.raises(AppError) as exc_info:
        recognizer(b"\x00" * 32000, "vi-VN")
    assert exc_info.value.code == "SPEECH_RATE_LIMITED"


@patch("requests.post")
def test_groq_recognizer_no_match(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "   "}
    mock_post.return_value = mock_response

    recognizer = GroqSpeechRecognizer("valid-key")
    with pytest.raises(AppError) as exc_info:
        recognizer(b"\x00" * 32000, "vi-VN")
    assert exc_info.value.code == "SPEECH_NO_MATCH"
