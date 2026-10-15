"""Prepare an isolated public demo without copying private local business data."""
import json
import os
import shutil
from pathlib import Path

from app.application.account_service import AccountService
from app.application.demo_database import import_demo_database
from app.data.account_repository import AccountRepository


def link_model(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / "runtime/public-demo/app"
    target.mkdir(parents=True, exist_ok=True)
    if not (target / "data").exists():
        shutil.copytree(root / "data", target / "data")
    for name in ("models", "index"):
        destination = target / "runtime" / name
        if not destination.exists():
            shutil.copytree(root / "runtime" / name, destination,
                            copy_function=link_model if name == "models" else shutil.copy2)
    result = import_demo_database(target)
    credentials = target / "runtime/demo/access.json"
    if not credentials.exists():
        import secrets
        repository = AccountRepository(target / "runtime/commerce/accounts.sqlite3")
        service = AccountService(repository)
        accounts = []
        for role in ("admin", "user"):
            email, password = f"cortis-public-{role}@example.test", secrets.token_urlsafe(32)
            service.register(email, f"Cortis public {role}", password, "explicit-public-demo-cli",
                             role=role, customer_id="C001" if role == "user" else None)
            accounts.append({"email": email, "password": password, "role": role})
        credentials.parent.mkdir(parents=True, exist_ok=True)
        credentials.write_text(json.dumps({"accounts": accounts}, indent=2) + "\n", encoding="utf-8")
    environment = target / ".env"
    if not environment.exists():
        environment.write_text("COOKIE_SECURE=true\nSPEECH_PROVIDER=groq\nGROQ_API_KEY=\nCORS_ORIGINS=http://127.0.0.1:5173\n", encoding="utf-8")
    print(json.dumps(result))
    print("Public demo ready in runtime/public-demo/app. Credentials remain local in its runtime/demo/access.json.")


if __name__ == "__main__":
    main()
