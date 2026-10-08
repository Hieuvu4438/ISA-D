"""Prepare and verify five authorized Azure cases; default mode never posts audio.

The backend owns the shared persistent SDK-call ledger. This script cannot reset
that ledger, silently retry a POST, record a microphone, or read an Azure key.
V001 must run through the real browser microphone; V002-V005 may use WAV upload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from filelock import FileLock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.application.speech_service import decode_wav  # noqa: E402 — local script adds the backend package path.
from app.domain import AppError  # noqa: E402

MANIFEST = ROOT / "evaluation/voice_cases.json"
WORK = ROOT / "runtime/speech"
BUDGET = ROOT / "runtime/speech-live-budget.json"
RESULTS = WORK / "live-results.json"


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def canonical_digest(value: dict) -> str:
    return digest(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def read_json(path: Path) -> dict:
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("JSON input exceeds the local audit limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def workspace_path(value: str, *, audio: bool = False) -> Path:
    path = Path(value)
    resolved = (path if path.is_absolute() else ROOT / path).resolve()
    if not resolved.is_relative_to(WORK.resolve()):
        raise ValueError("Speech inputs/evidence must stay under runtime/speech")
    if audio and resolved.suffix.lower() != ".wav":
        raise ValueError("Audio input must have the .wav extension")
    return resolved


def local_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("Only a local loopback HTTP backend is allowed")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Backend URL must be a plain loopback origin")
    return value.rstrip("/")


def load_manifest() -> dict:
    manifest = read_json(MANIFEST)
    cases = manifest.get("cases", [])
    if (
        manifest.get("schema_version") != 1
        or manifest.get("authorized_max_calls") != 5
        or len(cases) != 5
    ):
        raise ValueError("Expected the approved five-case voice manifest")
    if manifest.get("language") != "vi-VN" or manifest.get("region") != "southeastasia":
        raise ValueError("Voice region/language must match the approved configuration")
    ids = {case["case_id"] for case in cases}
    if len(ids) != 5:
        raise ValueError("Duplicate case identifiers")
    catalog = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    product_ids = {product["product_id"] for product in catalog}
    for case in cases:
        phrase = case.get("phrase_label")
        expected = case.get("expected_product_ids", [])
        if (
            not isinstance(phrase, str)
            or not 1 <= len(phrase) <= 500
            or not expected
            or not set(expected) <= product_ids
        ):
            raise ValueError("Invalid phrase label or expected product identifier")
        if case.get("execution_path") not in {"browser", "upload"}:
            raise ValueError("Unsupported case execution path")
    if not any(case.get("input_source") == "browser_real_microphone" for case in cases):
        raise ValueError("A real browser microphone case is required")
    if not any(
        case.get("input_source") == "human_recorded_wav_upload" for case in cases
    ):
        raise ValueError("A human-recorded WAV upload case is required")
    return manifest


def find_case(manifest: dict, case_id: str) -> dict:
    for case in manifest["cases"]:
        if case["case_id"] == case_id:
            return case
    raise ValueError("Unknown voice case")


def read_audio(path: Path) -> tuple[bytes, int]:
    if path.stat().st_size > 1048576:
        raise ValueError("WAV input exceeds 1 MiB")
    blob = path.read_bytes()
    _, duration_ms = decode_wav(blob)
    return blob, duration_ms


def validate_evidence(case: dict) -> None:
    evidence = read_json(
        workspace_path(case.get("capture_evidence_path") or "missing-evidence.json")
    )
    if (
        evidence.get("input_source") != case["input_source"]
        or evidence.get("human_speech") is not True
    ):
        raise ValueError(
            "Human speech and the declared capture method must be reviewed"
        )
    if (
        evidence.get("fake_audio") is not False
        or evidence.get("synthetic_voice") is not False
    ):
        raise ValueError("Synthetic/fake audio cannot satisfy the live gate")
    if not evidence.get("reviewer"):
        raise ValueError("Capture evidence needs an operator review")
    if case["input_source"] == "browser_real_microphone":
        if (
            evidence.get("fake_device") is not False
            or evidence.get("microphone_permission_observed") is not True
        ):
            raise ValueError(
                "Real device/permission evidence is required for the microphone case"
            )
        if case["execution_path"] != "browser":
            raise ValueError("The real microphone case must execute in the browser")


def audio_issues(manifest: dict) -> list[dict]:
    problems, hashes = [], set()
    for case in manifest["cases"]:
        try:
            blob, duration = read_audio(workspace_path(case["audio_path"], audio=True))
            audio_hash = digest(blob)
            if (
                case.get("audio_sha256") != audio_hash
                or case.get("audio_duration_ms") != duration
            ):
                raise ValueError("Audio was not bound or changed after review")
            if audio_hash in hashes:
                raise ValueError("The five cases need five distinct human recordings")
            hashes.add(audio_hash)
            if not case.get("human_audio_review"):
                raise ValueError(
                    "The recorded phrase has not been reviewed against its fixed label"
                )
            validate_evidence(case)
        except (OSError, ValueError, KeyError, TypeError, AppError) as error:
            problems.append(
                {
                    "case_id": case["case_id"],
                    "code": error.code
                    if isinstance(error, AppError)
                    else "RECORDING_NOT_READY",
                }
            )
    return problems


def configuration(base_url: str) -> dict:
    try:
        response = requests.get(
            base_url + "/api/v1/meta", timeout=10, allow_redirects=False
        )
        response.raise_for_status()
        speech = response.json().get("speech", {})
        return {
            "metadata_available": True,
            "configuration_ready": speech.get("configuration_state")
            == "configured_unverified",
            "expected_region": speech.get("region") == "southeastasia",
            "expected_language": speech.get("language") == "vi-VN",
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {
            "metadata_available": False,
            "configuration_ready": False,
            "expected_region": False,
            "expected_language": False,
        }


def budget_for(manifest: dict, *, required: bool = False) -> dict | None:
    if not BUDGET.exists():
        if required:
            raise ValueError("The shared five-call backend budget has not been armed")
        return None
    budget = read_json(BUDGET)
    if budget.get("schema_version") != 1 or budget.get("limit") != 5:
        raise ValueError("Invalid shared backend budget")
    attempts = budget.get("attempts")
    if not isinstance(attempts, list) or len(attempts) > 5:
        raise ValueError("Malformed shared speech budget")
    if budget.get("state") == "awaiting_fixtures":
        if attempts or budget.get("manifest_sha256") != "0" * 64 or required:
            raise ValueError(
                "The backend budget is locked until all reviewed fixtures are ready"
            )
        return budget
    if budget.get("state") != "armed" or budget.get(
        "manifest_sha256"
    ) != canonical_digest(manifest):
        raise ValueError(
            "Existing backend budget does not match the frozen manifest; never reset it to retry"
        )
    return budget


def require_frozen(manifest: dict) -> None:
    if (
        manifest.get("labels_frozen") is not True
        or manifest.get("labels_review", {}).get("status") != "approved"
    ):
        raise ValueError(
            "Phrase labels must be approved and frozen before any live calls"
        )
    if audio_issues(manifest):
        raise ValueError(
            "All five reviewed recordings must be ready before beginning the live gate"
        )
    if manifest.get("catalog_sha256") != digest(
        (ROOT / "data/products.json").read_bytes()
    ):
        raise ValueError("The catalog changed after label freeze")


def allow_fixture_preparation(manifest: dict) -> None:
    """An empty locked bootstrap may coexist with preparation, never with calls."""
    budget = budget_for(manifest)
    if budget is not None and budget.get("state") != "awaiting_fixtures":
        raise ValueError("Do not alter fixtures after the live session was armed")


def load_results() -> dict:
    if not RESULTS.exists():
        return {"schema_version": 1, "cases": {}}
    results = read_json(RESULTS)
    if results.get("cases"):
        if results.get("manifest_sha256") != canonical_digest(read_json(MANIFEST)):
            raise ValueError("Stored outcomes belong to a different frozen manifest")
        if not BUDGET.exists() or results.get("session_id") != read_json(BUDGET).get("session_id"):
            raise ValueError("Stored outcomes belong to a different live session")
    return results


def save_result(case_id: str, record: dict) -> None:
    results = load_results()
    results["manifest_sha256"] = canonical_digest(read_json(MANIFEST))
    results["session_id"] = read_json(BUDGET)["session_id"]
    results["cases"][case_id] = record
    write_json(RESULTS, results)


def import_recognized(
    case: dict, response: dict, budget: dict, execution_path: str
) -> dict:
    matches = [
        attempt
        for attempt in budget["attempts"]
        if attempt.get("audio_sha256") == case["audio_sha256"]
    ]
    if len(matches) != 1 or matches[0].get("status") != "recognized":
        raise ValueError("No unique completed real SDK attempt matches this WAV")
    text = response.get("transcript")
    if (
        response.get("provider") != "azure"
        or response.get("language") != "vi-VN"
        or not isinstance(text, str)
        or not text.strip()
        or len(text) > 500
    ):
        raise ValueError("Expected an actual nonempty Azure vi-VN response")
    if response.get("audio_duration_ms") != case["audio_duration_ms"]:
        raise ValueError("Response duration does not match the reviewed WAV")
    return {
        "case_id": case["case_id"],
        "audio_sha256": case["audio_sha256"],
        "attempt_id": matches[0]["attempt_id"],
        "execution_path": execution_path,
        "status": "recognized",
        "request_id": response.get("request_id"),
        "original_transcript": text,
        "observed_at": utc_now(),
        "semantic_original_pass": None,
        "semantic_reviewer": None,
        "confirmed_transcript": None,
        "retrieval_original": None,
        "retrieval_confirmed": None,
    }


def run_upload(case: dict, manifest: dict, base_url: str) -> None:
    if case["execution_path"] == "browser":
        raise ValueError(
            "The microphone case must be executed in the real frontend, then collected"
        )
    budget = budget_for(manifest, required=True)
    if len(budget["attempts"]) >= 5 or any(
        a.get("audio_sha256") == case["audio_sha256"] for a in budget["attempts"]
    ):
        raise ValueError(
            "Case already consumed a dispatch or no quota remains; no automatic/manual replay by this script"
        )
    if case["case_id"] in load_results()["cases"]:
        raise ValueError("Case already has a recorded outcome")
    blob, _ = read_audio(workspace_path(case["audio_path"], audio=True))
    record = {
        "case_id": case["case_id"],
        "audio_sha256": case["audio_sha256"],
        "execution_path": "upload",
        "observed_at": utc_now(),
    }
    started = time.perf_counter()
    # Exactly one application POST; requests' default adapter has no retry loop.
    try:
        response = requests.post(
            base_url + "/api/v1/speech/transcriptions",
            files={"audio": ("recording.wav", blob, "audio/wav")},
            data={"language": "vi-VN"},
            timeout=(5, 35),
            allow_redirects=False,
        )
        record["http_status"] = response.status_code
        body = response.json()
        if response.status_code == 200:
            record.update(
                import_recognized(
                    case, body, budget_for(manifest, required=True), "upload"
                )
            )
        else:
            record["status"] = (
                body.get("code") if isinstance(body.get("code"), str) else "HTTP_ERROR"
            )
            record["request_id"] = body.get("request_id")
    except requests.RequestException:
        record["status"] = "TRANSPORT_ERROR_OR_TIMEOUT"
    except (ValueError, TypeError, KeyError):
        record["status"] = "RESPONSE_OR_LEDGER_UNVERIFIED"
    record["http_elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    save_result(case["case_id"], record)
    print(json.dumps({"case_id": case["case_id"], "status": record["status"]}))


def search_transcript(base_url: str, text: str, expected: list[str]) -> dict:
    response = requests.post(
        base_url + "/api/v1/search",
        json={
            "mode": "voice",
            "text": text,
            "voice_source": "azure",
            "options": {"top_k": 3, "result_policy": "nearest", "filters": {}},
        },
        timeout=(5, 15),
        allow_redirects=False,
    )
    response.raise_for_status()
    body = response.json()
    product_ids = [item["product"]["product_id"] for item in body.get("results", [])]
    return {
        "request_id": body.get("request_id"),
        "top3_product_ids": product_ids,
        "expected_in_top3": bool(set(product_ids) & set(expected)),
    }


def report(manifest: dict, base_url: str) -> dict:
    issues = audio_issues(manifest)
    budget = budget_for(manifest)
    attempts = budget["attempts"] if budget else []
    records = load_results()["cases"]
    allowed_hashes = {
        case.get("audio_sha256")
        for case in manifest["cases"]
        if case.get("audio_sha256")
    }
    recognized = sum(
        record.get("status") == "recognized" for record in records.values()
    )
    semantic = sum(
        record.get("status") == "recognized"
        and record.get("semantic_original_pass") is True
        for record in records.values()
    )
    retrieved = sum(
        record.get("retrieval_confirmed", {}).get("expected_in_top3") is True
        for record in records.values()
        if isinstance(record.get("retrieval_confirmed"), dict)
    )
    mic_verified = any(
        case["execution_path"] == "browser"
        and records.get(case["case_id"], {}).get("execution_path") == "browser"
        and records.get(case["case_id"], {}).get("status") == "recognized"
        for case in manifest["cases"]
    )
    complete_attempts = len(attempts) == 5 and all(
        a.get("status") != "reserved" and a.get("finished_at") for a in attempts
    )
    fixtures_match = (
        bool(attempts)
        and len({a.get("audio_sha256") for a in attempts}) == len(attempts)
        and all(a.get("audio_sha256") in allowed_hashes for a in attempts)
    )
    passed = (
        not issues
        and manifest.get("labels_frozen") is True
        and complete_attempts
        and fixtures_match
        and recognized >= 4
        and semantic >= 4
        and retrieved >= 4
        and mic_verified
    )
    value = {
        "status": "passed" if passed else "pending_or_failed",
        "configuration": configuration(base_url),
        "labels_frozen": manifest.get("labels_frozen") is True,
        "manifest_sha256": canonical_digest(manifest),
        "recording_issues": issues,
        "budget_armed": budget is not None and budget.get("state") == "armed",
        "sdk_dispatches_consumed": len(attempts),
        "remaining_dispatches": 5 - len(attempts),
        "total_audio_duration_ms": sum(a.get("duration_ms", 0) for a in attempts),
        "all_five_attempts_finished": complete_attempts,
        "attempts_match_distinct_frozen_fixtures": fixtures_match,
        "nonempty_recognition_count": recognized,
        "original_semantic_pass_count": semantic,
        "confirmed_search_expected_top3_count": retrieved,
        "real_browser_mic_path_verified": mic_verified,
        "cases": [
            {
                "case_id": case["case_id"],
                "phrase_label": case["phrase_label"],
                "expected_product_ids": case["expected_product_ids"],
                "result": records.get(case["case_id"]),
            }
            for case in manifest["cases"]
        ],
        "reported_at": utc_now(),
        "billing_cost": "not asserted; no billing evidence",
    }
    write_json(WORK / "live-report.json", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-calls", type=int, choices=[5], default=5)
    parser.add_argument("--confirm-live", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--bind-audio", metavar="CASE")
    action.add_argument("--freeze-labels", action="store_true")
    action.add_argument("--arm-budget", action="store_true")
    action.add_argument("--case", metavar="CASE")
    action.add_argument("--collect-browser", metavar="CASE")
    action.add_argument("--review-original", metavar="CASE")
    action.add_argument("--confirm-transcript", metavar="CASE")
    parser.add_argument("--audio")
    parser.add_argument("--capture-evidence")
    parser.add_argument("--response-file")
    parser.add_argument("--reviewer")
    parser.add_argument("--semantic-match", choices=["pass", "fail"])
    parser.add_argument("--confirmed-text-file")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    with FileLock(str(WORK / "verification.lock"), timeout=1):
        manifest = load_manifest()
        base_url = local_base_url(args.base_url)
        if args.bind_audio:
            allow_fixture_preparation(manifest)
            if manifest.get("labels_frozen"):
                raise ValueError(
                    "Do not change frozen recordings or an already armed session"
                )
            if not args.audio or not args.capture_evidence or not args.reviewer:
                raise ValueError(
                    "Binding needs --audio, --capture-evidence and --reviewer after listening to the real recording"
                )
            case = find_case(manifest, args.bind_audio)
            blob, duration = read_audio(workspace_path(args.audio, audio=True))
            evidence_path = workspace_path(args.capture_evidence)
            case["capture_evidence_path"] = evidence_path.relative_to(ROOT).as_posix()
            validate_evidence(case)
            target = workspace_path(case["audio_path"], audio=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            case.update(
                audio_sha256=digest(blob),
                audio_duration_ms=duration,
                human_audio_review={
                    "reviewer": args.reviewer,
                    "reviewed_at": utc_now(),
                    "phrase_matches_fixed_label": True,
                },
            )
            write_json(MANIFEST, manifest)
        elif args.freeze_labels:
            allow_fixture_preparation(manifest)
            if (
                audio_issues(manifest)
                or manifest.get("labels_review", {}).get("status") != "approved"
            ):
                raise ValueError(
                    "Freeze requires all five actual reviewed WAVs and preapproved labels"
                )
            if not manifest.get("labels_frozen"):
                manifest.update(
                    labels_frozen=True,
                    frozen_at=utc_now(),
                    catalog_sha256=digest((ROOT / "data/products.json").read_bytes()),
                )
                write_json(MANIFEST, manifest)
        elif args.arm_budget:
            require_frozen(manifest)
            with FileLock(str(BUDGET) + ".lock", timeout=1):
                if BUDGET.exists():
                    existing = budget_for(manifest)
                    if existing["state"] == "awaiting_fixtures":
                        existing.update(
                            state="armed", manifest_sha256=canonical_digest(manifest)
                        )
                        write_json(BUDGET, existing)
                    else:
                        budget_for(manifest, required=True)
                        print(
                            json.dumps(
                                {"budget_already_armed": True, "reset_performed": False}
                            )
                        )
                else:
                    budget = {
                        "schema_version": 1,
                        "state": "armed",
                        "limit": 5,
                        "session_id": str(uuid4()),
                        "manifest_sha256": canonical_digest(manifest),
                        "attempts": [],
                    }
                    BUDGET.parent.mkdir(parents=True, exist_ok=True)
                    with BUDGET.open("x", encoding="utf-8") as output:
                        output.write(json.dumps(budget, ensure_ascii=False, indent=2))
                        output.flush()
                        os.fsync(output.fileno())
        elif args.collect_browser:
            require_frozen(manifest)
            case = find_case(manifest, args.collect_browser)
            if case["execution_path"] != "browser" or not args.response_file:
                raise ValueError(
                    "Collect the actual browser microphone response with --response-file"
                )
            if case["case_id"] in load_results()["cases"]:
                raise ValueError(
                    "A case outcome cannot be replaced to improve the gate score"
                )
            body = read_json(workspace_path(args.response_file))
            save_result(
                case["case_id"],
                import_recognized(
                    case, body, budget_for(manifest, required=True), "browser"
                ),
            )
        elif args.review_original:
            require_frozen(manifest)
            if not args.reviewer or not args.semantic_match:
                raise ValueError(
                    "Semantic review needs --reviewer and --semantic-match pass|fail"
                )
            case = find_case(manifest, args.review_original)
            record = load_results()["cases"].get(case["case_id"])
            if (
                not record
                or record.get("status") != "recognized"
                or record.get("semantic_original_pass") is not None
            ):
                raise ValueError(
                    "Only an actual unreviewed original Azure transcript can be scored once"
                )
            record.update(
                semantic_original_pass=args.semantic_match == "pass",
                semantic_reviewer=args.reviewer,
            )
            save_result(case["case_id"], record)
        elif args.confirm_transcript:
            require_frozen(manifest)
            if not args.reviewer:
                raise ValueError("Transcript confirmation needs an explicit reviewer")
            case = find_case(manifest, args.confirm_transcript)
            record = load_results()["cases"].get(case["case_id"])
            if (
                not record
                or record.get("status") != "recognized"
                or record.get("confirmed_transcript") is not None
            ):
                raise ValueError(
                    "Confirm an actual Azure result once; do not replace recorded retrieval to improve its score"
                )
            text = (
                workspace_path(args.confirmed_text_file)
                .read_text(encoding="utf-8")
                .strip()
                if args.confirmed_text_file
                else record["original_transcript"]
            )
            if not 1 <= len(text) <= 500:
                raise ValueError("Confirmed transcript must contain 1-500 characters")
            record.update(
                confirmed_transcript=text, confirmation_reviewer=args.reviewer
            )
            record["retrieval_original"] = search_transcript(
                base_url, record["original_transcript"], case["expected_product_ids"]
            )
            record["retrieval_confirmed"] = (
                record["retrieval_original"]
                if text == record["original_transcript"]
                else search_transcript(base_url, text, case["expected_product_ids"])
            )
            save_result(case["case_id"], record)
        elif args.confirm_live:
            require_frozen(manifest)
            budget_for(manifest, required=True)
            config = configuration(base_url)
            if not all(config.values()):
                raise ValueError(
                    "Backend speech configuration is not ready; no transcription was sent"
                )
            cases = (
                [find_case(manifest, args.case)]
                if args.case
                else [
                    case
                    for case in manifest["cases"]
                    if case["execution_path"] == "upload"
                ]
            )
            for case in cases:
                budget = budget_for(manifest, required=True)
                if any(
                    a.get("audio_sha256") == case["audio_sha256"]
                    for a in budget["attempts"]
                ):
                    continue
                run_upload(case, manifest, base_url)
        elif args.case:
            raise ValueError(
                "Live transcription requires the explicit --confirm-live flag"
            )
        value = report(manifest, base_url)
        print(
            json.dumps(
                {
                    key: value[key]
                    for key in value
                    if key not in {"cases", "manifest_sha256", "reported_at"}
                },
                ensure_ascii=False,
            )
        )
        return (
            0
            if value["status"] == "passed"
            or any(
                [
                    args.bind_audio,
                    args.freeze_labels,
                    args.arm_budget,
                    args.collect_browser,
                    args.review_original,
                    args.confirm_transcript,
                    args.confirm_live,
                ]
            )
            else 2
        )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AppError,
        requests.RequestException,
    ):
        # Do not echo arbitrary local file contents, provider exceptions or secrets.
        print(
            json.dumps(
                {
                    "status": "precondition_or_local_request_failed",
                    "provider_retry_performed": False,
                }
            )
        )
        raise SystemExit(2) from None
