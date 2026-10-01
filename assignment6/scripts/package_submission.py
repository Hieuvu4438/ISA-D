"""Build a curated reproducible ZIP after validation and clean extraction smoke."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_submission import validate

FIXED_DATE = (2026, 10, 1, 0, 0, 0)


def selected_files(root):
    selected = set()
    for directory in ["application", "presentation", "data", "evaluation", "docs", "tests"]:
        for path in (root / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                selected.add(path)
    for name in [
        "main.py",
        "README.md",
        ".gitignore",
        ".gitattributes",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-automation.txt",
    ]:
        path = root / name
        if path.is_file():
            selected.add(path)
    for path in (root / "scripts").rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".py", ".java", ".xml"}
            and "classes" not in path.parts
            and "__pycache__" not in path.parts
        ):
            selected.add(path)
    for directory in ["artifacts/diagrams", "artifacts/demo", "artifacts/evaluation", "artifacts/tests"]:
        for path in (root / directory).glob("*"):
            if (
                path.is_file()
                and path.suffix in {".png", ".txt", ".json", ".csv", ".xml"}
                and "_pending" not in path.name
            ):
                selected.add(path)
    for path in (root / "artifacts/screenshots").glob("*"):
        if path.is_file() and path.suffix in {".png", ".json"} and path.name.startswith(("vp_", "demo_")):
            selected.add(path)
    for relative in [
        "models/Assignment_06_Multimodal_Search.vpp",
        "artifacts/report/Assignment_06_Report.pdf",
        "artifacts/report/REVIEW.md",
        "artifacts/report/build_audit.json",
        "artifacts/automation/model_inventory.json",
        "artifacts/automation/reopened_inventory.json",
        "artifacts/automation/verify_result.txt",
        "artifacts/automation/refine_result.txt",
    ]:
        path = root / relative
        if path.is_file():
            selected.add(path)
    return sorted(selected, key=lambda p: p.relative_to(root).as_posix())


def smoke_clean_extraction(root, files, interpreter):
    test_root = root / "artifacts/tests"
    test_root.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    commands = [
        ["main.py", "--demo", "--json"],
        ["main.py", "--mode", "text", "--query", "black shoes", "--json"],
        ["main.py", "--mode", "voice", "--query", "find black running shoes", "--json"],
        ["main.py", "--mode", "image", "--image", "data/queries/black_shoe_query.png", "--json"],
        ["-m", "pytest", "-q"],
    ]
    runs = []
    with tempfile.TemporaryDirectory(prefix="submission-smoke-", dir=test_root) as temporary:
        extracted = Path(temporary)
        # Build a ZIP snapshot, then really extract it; no imports use source workspace.
        snapshot = extracted / "snapshot.zip"
        with zipfile.ZipFile(snapshot, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(root).as_posix())
        destination = extracted / "clean"
        with zipfile.ZipFile(snapshot) as archive:
            archive.extractall(destination)
        checks = validate(destination)
        if not checks["passed"]:
            raise RuntimeError("Clean extraction validation failed: " + json.dumps(checks))
        for args in commands:
            completed = subprocess.run(
                [str(interpreter), *args],
                cwd=destination,
                env=environment,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=90,
            )
            record = {
                "command": [str(interpreter), *args],
                "cwd": "clean extracted assignment root",
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            runs.append(record)
            if completed.returncode:
                raise RuntimeError("Clean extraction command failed: " + json.dumps(record))
            if args[0] == "main.py":
                payload = json.loads(completed.stdout)
                if isinstance(payload, list):
                    assert {"text", "voice", "image"} <= {p["query"]["type"] for p in payload}
                else:
                    assert payload["results"] and "final_score" in payload["results"][0]
        return {
            "passed": True,
            "dependency_environment": "workspace .venv interpreter; dependencies reused, extracted source isolated",
            "validation": checks,
            "runs": runs,
        }


def write_final_verification(root, validation, smoke):
    tests = next(c["details"] for c in validation["checks"] if c["name"].startswith("Test, coverage"))
    lines = [
        "# Final Verification — Assignment 06",
        "",
        "Bản bàn giao được kiểm tra từ file thật, service output, native model inventory và ZIP extraction sạch. Báo cáo PDF dùng đúng `artifacts/report/Assignment_06_Report.pdf`.",
        "",
        "| Gate | Kết quả |",
        "|---|---|",
    ]
    lines.extend(f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} |" for c in validation["checks"])
    lines.extend(
        [
            "",
            f"Tests: **{tests['tests']} PASS**, failures/errors={tests['failures']}, skipped={tests['skipped']}; application/data line coverage **{tests['application_data_line_coverage']:.2f}%**. Ruff/typecheck/pip-check evidence PASS. PDF exactly 12 nonempty pages; required 3 UML exports and 6 screenshots exist and decode.",
            "",
            "Clean extraction smoke dùng interpreter `.venv` của workspace để reuse dependency, nhưng chạy source từ ZIP snapshot giải nén trong cwd riêng, không dùng PYTHONPATH workspace. Đây là portable-source smoke, không tuyên bố clean dependency installation.",
            "",
            "Các lệnh đã chạy thành công từ cwd của source giải nén, gọi đường dẫn interpreter workspace tuyệt đối:",
            "",
            "```powershell",
        ]
    )
    lines.extend(f'& "{run["command"][0]}" ' + subprocess.list2cmdline(run["command"][1:]) for run in smoke["runs"])
    lines.extend(
        [
            "```",
            "",
            "Kết quả chi tiết: `artifacts/tests/submission_validation.json`, `artifacts/tests/clean_extraction.json`. Ground-truth và results được đối chiếu SHA-256/IDs/counts; primary, extension, challenge, robustness có denominator riêng. Challenge failures được giữ nguyên trong report/evaluation.",
            "",
            "ZIP chọn source Python, dataset/image/query fixtures, frozen ground truth, docs, report PDF, native `.vpp`, UML exports, assignment screenshots, test/demo/evaluation evidence, desktop script và Java/XML plugin source. Không đưa `.venv`, backup, VP seed/workspace/plugin classes, ảnh project cũ, source PDF đề vào ZIP.",
            "",
            "Manifest chứa SHA-256 và byte size cho mỗi file payload, không hash chính manifest. Timestamp ZIP cố định giúp tái tạo byte-identical archive từ cùng input. `submission/manifest.json` ngoài ZIP bổ sung SHA-256 của archive; ZIP hash không được ghi vào manifest bên trong để tránh vòng tự tham chiếu.",
            "",
            "Giới hạn: voice là simulated STT; ảnh synthetic và pixel descriptor không phải semantic learned encoder; order context không phải production authentication; chưa nộp LMS. Native model inventory chứng minh object types; việc reopen/render thật trong Visual Paradigm do root ghi ở progress/screenshots.",
            "",
        ]
    )
    (root / "docs/FINAL_VERIFICATION.md").write_text("\n".join(lines), encoding="utf-8")


def package(root=ROOT, output=None, interpreter=None):
    root = Path(root).resolve()
    output = Path(output or root / "submission/Assignment_06_Submission.zip").resolve()
    interpreter = Path(interpreter or root / ".venv/Scripts/python.exe").resolve()
    validation = validate(root)
    if not validation["passed"]:
        raise RuntimeError("Deliverables are not ready: " + json.dumps(validation, ensure_ascii=False))
    smoke = smoke_clean_extraction(root, selected_files(root), interpreter)
    (root / "artifacts/tests/submission_validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root / "artifacts/tests/clean_extraction.json").write_text(
        json.dumps(smoke, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_final_verification(root, validation, smoke)
    payloads = {path.relative_to(root).as_posix(): path.read_bytes() for path in selected_files(root)}
    manifest = {
        "format": "assignment06-sha256-v1",
        "assignment": "06",
        "archive_path": output.name,
        "file_count": len(payloads),
        "files": [
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in payloads.items()
        ],
        "self_hash_policy": "manifest.json excluded from own file list; archive hash only in external manifest",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in [
                *payloads.items(),
                ("manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
            ]:
                info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None, "Corrupted archive"
            for record in manifest["files"]:
                data = archive.read(record["path"])
                assert hashlib.sha256(data).hexdigest() == record["sha256"], "Archive checksum mismatch"
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    external_manifest = dict(
        manifest,
        archive={
            "path": output.name,
            "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        },
        validation_passed=True,
        clean_extraction_passed=True,
    )
    (output.parent / "manifest.json").write_text(
        json.dumps(external_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return external_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--python", type=Path, help="absolute interpreter for isolated source smoke")
    args = parser.parse_args()
    result = package(args.root, args.output, args.python)
    print(
        json.dumps(
            {
                "file_count": result["file_count"],
                "archive": result["archive"],
                "validation_passed": result["validation_passed"],
                "clean_extraction_passed": result["clean_extraction_passed"],
            },
            indent=2,
        )
    )
