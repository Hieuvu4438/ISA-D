from dataclasses import dataclass, field
import os
import math
from pathlib import Path

from dotenv import load_dotenv

TEXT_MODEL_ID = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
IMAGE_MODEL_ID = "sentence-transformers/clip-ViT-B-32"
TEXT_REVISION = "58edf8cada9e398793dca955574a48cbb7f18be2"
IMAGE_REVISION = "327ab6726d33c0e22f920c83f2ff9e4bd38ca37f"


@dataclass
class Settings:
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    speech_key: str = field(default="", repr=False)
    speech_region: str = "southeastasia"
    speech_language: str = "vi-VN"
    speech_timeout: float = 25.0
    speech_provider: str = "azure"
    local_speech_model_path: Path | None = None
    local_speech_cpu_threads: int = 4
    local_speech_timeout: float = 90.0
    search_timeout: float = 10.0
    customer_id: str = "C001"
    load_models: bool = True

    def __post_init__(self):
        if not 1 <= self.local_speech_cpu_threads <= 16:
            raise ValueError("LOCAL_SPEECH_CPU_THREADS must be between 1 and 16")
        if not math.isfinite(self.local_speech_timeout) or not 1 <= self.local_speech_timeout <= 90:
            raise ValueError("LOCAL_SPEECH_TIMEOUT must be between 1 and 90 seconds")

    @classmethod
    def from_env(cls):
        root = Path(__file__).resolve().parents[2]
        load_dotenv(root / ".env", override=False)
        return cls(
            root=root,
            speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
            speech_region=os.getenv("AZURE_SPEECH_REGION", "southeastasia"),
            speech_language=os.getenv("AZURE_SPEECH_LANGUAGE", "vi-VN"),
            speech_provider=os.getenv("SPEECH_PROVIDER", "azure").strip().lower(),
            local_speech_model_path=Path(os.getenv("LOCAL_SPEECH_MODEL_PATH", "").strip()
                                         or root / "models" / "speech-whisper-small"),
            local_speech_cpu_threads=int(os.getenv("LOCAL_SPEECH_CPU_THREADS", "4")),
            local_speech_timeout=float(os.getenv("LOCAL_SPEECH_TIMEOUT", "90")),
            customer_id=os.getenv("DEMO_CUSTOMER_ID", "C001"),
        )
