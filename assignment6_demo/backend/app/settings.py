from dataclasses import dataclass, field
import os
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
    search_timeout: float = 10.0
    customer_id: str = "C001"
    load_models: bool = True

    @classmethod
    def from_env(cls):
        root = Path(__file__).resolve().parents[2]
        load_dotenv(root / ".env", override=False)
        return cls(
            root=root,
            speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
            speech_region=os.getenv("AZURE_SPEECH_REGION", "southeastasia"),
            speech_language=os.getenv("AZURE_SPEECH_LANGUAGE", "vi-VN"),
            customer_id=os.getenv("DEMO_CUSTOMER_ID", "C001"),
        )
