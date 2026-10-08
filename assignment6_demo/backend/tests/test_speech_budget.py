"""The live acceptance budget is persistent and includes failed provider attempts."""

import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.application.speech_service import SpeechService
from app.data.speech_budget import SpeechBudget
from app.domain import AppError
from test_speech import wav


def arm(root):
    path = root / "runtime/speech-live-budget.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema_version": 1, "state": "armed", "limit": 5, "session_id": "test-session",
        "manifest_sha256": "a" * 64, "attempts": [],
    }))
    return path


def test_budget_survives_instances_and_refuses_sixth_call(tmp_path):
    path = arm(tmp_path)
    for _ in range(5):
        budget = SpeechBudget(tmp_path)
        attempt = budget.reserve(wav(), 1000)
        budget.finish(attempt, "recognized")
    with pytest.raises(AppError) as caught:
        SpeechBudget(tmp_path).reserve(wav(), 1000)
    assert caught.value.code == "SPEECH_UNAVAILABLE"
    ledger = json.loads(path.read_text())
    assert len(ledger["attempts"]) == 5
    assert ledger["attempts"][0]["audio_sha256"] == hashlib.sha256(wav()).hexdigest()
    assert all(a["status"] == "recognized" for a in ledger["attempts"])


def test_invalid_audio_does_not_consume_budget_and_provider_error_does(tmp_path):
    path = arm(tmp_path)
    calls = []

    def provider(*_):
        calls.append(1)
        raise AppError(502, "SPEECH_AUTH_FAILED", "safe")

    config = SimpleNamespace(root=tmp_path, speech_key="test-only", speech_region="southeastasia",
                             speech_language="vi-VN", speech_timeout=1)
    service = SpeechService(config, provider=provider)
    try:
        with pytest.raises(AppError):
            asyncio.run(service.transcribe(b"invalid"))
        assert json.loads(path.read_text())["attempts"] == []
        with pytest.raises(AppError):
            asyncio.run(service.transcribe(wav()))
        ledger = json.loads(path.read_text())
        assert calls == [1]
        assert ledger["attempts"][0]["status"] == "SPEECH_AUTH_FAILED"
        assert "test-only" not in path.read_text()
    finally:
        service.close()


def test_missing_and_corrupt_budget_fail_closed(tmp_path):
    budget = SpeechBudget(tmp_path)
    with pytest.raises(AppError):
        budget.reserve(wav(), 1000)
    assert SpeechBudget(None).reserve(wav(), 1000) is None  # Isolated provider doubles only.
    path = arm(tmp_path)
    path.write_text("broken")
    with pytest.raises(AppError):
        budget.reserve(wav(), 1000)


def test_awaiting_fixtures_budget_blocks_provider(tmp_path):
    path = arm(tmp_path)
    ledger = json.loads(path.read_text())
    ledger["state"] = "awaiting_fixtures"
    path.write_text(json.dumps(ledger))
    with pytest.raises(AppError):
        SpeechBudget(tmp_path).reserve(wav(), 1000)
    assert json.loads(path.read_text())["attempts"] == []
