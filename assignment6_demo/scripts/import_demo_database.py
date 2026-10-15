"""Import the versioned public demo snapshot; never reset an already-used database."""
import json
from pathlib import Path

from app.application.demo_database import import_demo_database

if __name__ == "__main__":
    result = import_demo_database(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2))
