"""Optional local acceptance ledger; no audio, transcript or credentials are stored."""

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from filelock import FileLock

from app.domain import AppError


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SpeechBudget:
    def __init__(self, root):
        self.path = root / "runtime/speech-live-budget.json" if root is not None else None

    def _read(self):
        if self.path.stat().st_size > 16384:
            raise ValueError("oversized ledger")
        ledger = json.loads(self.path.read_text(encoding="utf-8"))
        if (ledger.get("schema_version") != 1 or ledger.get("state") != "armed"
                or type(ledger.get("limit")) is not int
                or ledger["limit"] != 5 or not isinstance(ledger.get("session_id"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", ledger.get("manifest_sha256", ""))
                or not isinstance(ledger.get("attempts"), list) or len(ledger["attempts"]) > 5):
            raise ValueError("invalid ledger")
        for attempt in ledger["attempts"]:
            if (not isinstance(attempt, dict) or not isinstance(attempt.get("attempt_id"), str)
                    or not re.fullmatch(r"[a-f0-9]{64}", attempt.get("audio_sha256", ""))):
                raise ValueError("invalid attempt")
        return ledger

    def _write(self, ledger):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def reserve(self, audio, duration_ms):
        if self.path is None:
            return None
        try:
            if not self.path.exists():
                raise ValueError("acceptance budget not armed")
            with FileLock(str(self.path) + ".lock", timeout=1):
                ledger = self._read()
                if len(ledger["attempts"]) >= ledger["limit"]:
                    raise ValueError("exhausted budget")
                attempt_id = str(uuid4())
                ledger["attempts"].append({
                    "attempt_id": attempt_id, "audio_sha256": hashlib.sha256(audio).hexdigest(),
                    "duration_ms": duration_ms, "started_at": timestamp(),
                    "finished_at": None, "status": "reserved",
                })
                # Reserve before dispatch; a crash or timeout never refunds an attempt.
                self._write(ledger)
                return attempt_id
        except Exception:
            raise AppError(503, "SPEECH_UNAVAILABLE",
                           "Đợt kiểm tra Azure đã hết lượt hoặc bộ đếm chưa hợp lệ.") from None

    def finish(self, attempt_id, status):
        if attempt_id is None:
            return
        allowed = {"recognized", "SPEECH_NO_MATCH", "SPEECH_AUTH_FAILED", "SPEECH_RATE_LIMITED",
                   "SPEECH_TIMEOUT", "SPEECH_UPSTREAM_FAILED", "SPEECH_UNAVAILABLE"}
        status = status if status in allowed else "SPEECH_UPSTREAM_FAILED"
        try:
            with FileLock(str(self.path) + ".lock", timeout=1):
                ledger = self._read()
                attempt = next(a for a in ledger["attempts"] if a["attempt_id"] == attempt_id)
                attempt.update(status=status, finished_at=timestamp())
                self._write(ledger)
        except Exception:
            # An unfinished reservation still consumes quota and prevents extra calls.
            pass
