"""Fetch a bounded sample of licensed, real Vietnamese FLEURS test speech.

Only the beginning of the compressed archive is streamed; the 544 MB archive
is never downloaded in full. Audio and reference text remain in ignored runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import numpy as np
import requests
from scipy.io import wavfile

REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
BASE = f"https://huggingface.co/datasets/google/fleurs/resolve/{REVISION}/data/vi_vn"
LIMIT = 30 * 1024 * 1024


class LimitedReader:
    """Bound network reads even if early archive entries are unsuitable."""

    def __init__(self, raw: object) -> None:
        self.raw = raw
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        remaining = LIMIT - self.bytes_read
        if remaining <= 0:
            raise RuntimeError("Reached the 30 MiB download limit")
        data = self.raw.read(min(size if size >= 0 else remaining, remaining))
        self.bytes_read += len(data)
        return data


def fetch(output: Path, count: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    response = requests.get(f"{BASE}/test.tsv", timeout=30)
    response.raise_for_status()
    references = {}
    for line in response.text.splitlines():
        fields = line.split("\t")
        if len(fields) >= 7:
            references[fields[1]] = fields

    cases = []
    used_text = set()
    archive_url = f"{BASE}/audio/test.tar.gz"
    with requests.get(archive_url, stream=True, timeout=(15, 30)) as archive_response:
        archive_response.raise_for_status()
        reader = LimitedReader(archive_response.raw)
        with tarfile.open(fileobj=reader, mode="r|gz") as archive:
            for member in archive:
                name = Path(member.name).name
                fields = references.get(name)
                if (
                    not member.isfile()
                    or not fields
                    or fields[2] in used_text
                    or not 1 <= int(fields[5]) / 16000 <= 15
                ):
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    continue
                original = stream.read()
                rate, audio = wavfile.read(io.BytesIO(original))
                if rate != 16000 or audio.ndim != 1:
                    continue
                if np.issubdtype(audio.dtype, np.floating):
                    pcm = np.round(np.clip(audio, -1, 1) * 32767).astype(np.int16)
                elif audio.dtype == np.int16:
                    pcm = audio
                else:
                    raise ValueError(f"Unexpected audio dtype: {audio.dtype}")
                destination = output / f"fleurs-vi-{len(cases) + 1:02d}.wav"
                wavfile.write(destination, rate, pcm)
                case = {
                    "id": f"FLEURS-VI-{len(cases) + 1:02d}",
                    "audio_path": destination.name,
                    "reference": fields[2],
                    "normalized_reference": fields[3],
                    "speaker_gender": fields[6],
                    "original_filename": name,
                    "duration_seconds": len(pcm) / rate,
                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    "original_sha256": hashlib.sha256(original).hexdigest(),
                    "format": "PCM16 mono 16000 Hz",
                    "synthesized": False,
                }
                cases.append(case)
                used_text.add(fields[2])
                print(f"Fetched {case['id']}: {case['duration_seconds']:.2f}s", flush=True)
                if len(cases) == count:
                    break
    report = {
        "dataset": "google/fleurs",
        "configuration": "vi_vn",
        "split": "test",
        "revision": REVISION,
        "source": "https://huggingface.co/datasets/google/fleurs",
        "audio_archive_url": archive_url,
        "reference_url": f"{BASE}/test.tsv",
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Conneau et al., FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech (2022), Google FLEURS dataset.",
        "purpose": "Independent real Vietnamese STT smoke test; not shop-specific microphone acceptance",
        "downloaded_archive_bytes": reader.bytes_read,
        "cases": cases,
    }
    (output / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if len(cases) != count:
        raise RuntimeError(f"Only {len(cases)} of {count} eligible cases found")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, choices=range(1, 11), default=5)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[1] / "runtime" / "speech-evaluation",
    )
    args = parser.parse_args()
    report = fetch(args.output, args.count)
    print(json.dumps({"cases": len(report["cases"]), "archive_bytes": report["downloaded_archive_bytes"]}))


if __name__ == "__main__":
    main()
