"""Explicitly provision local customer-demo accounts; never called at startup or CI."""
import json
import secrets
from pathlib import Path

from app.application.account_service import AccountService
from app.data.account_repository import AccountRepository
from app.settings import Settings


def main():
    root = Path(__file__).resolve().parents[1]
    settings = Settings.from_env()
    if settings.root.resolve() != root:
        raise SystemExit("Demo accounts must stay in this workspace")
    destination = root / "runtime/demo/access.json"
    repository = AccountRepository(root / "runtime/commerce/accounts.sqlite3")
    if destination.exists():
        saved = json.loads(destination.read_text(encoding="utf-8"))
        with repository.connection() as db:
            for account in saved["accounts"]:
                row = db.execute("SELECT role FROM accounts WHERE email=?", (account["email"],)).fetchone()
                if row is None or row[0] != account["role"]:
                    raise SystemExit("Saved demo accounts changed; review them before provisioning again")
        print("Demo accounts already prepared; credentials unchanged in runtime/demo/access.json")
        return
    specifications = [("cortis-demo-admin@example.test", "Cortis demo admin", "admin"),
                      ("cortis-demo-user@example.test", "Cortis demo user", "user")]
    with repository.connection() as db:
        for email, _, _ in specifications:
            if db.execute("SELECT 1 FROM accounts WHERE email=?", (email,)).fetchone():
                raise SystemExit("A demo email already exists; no password or role was overwritten")
    service = AccountService(repository)
    accounts = []
    for email, name, role in specifications:
        password = secrets.token_urlsafe(32)
        service.register(email, name, password, "explicit-demo-cli", role=role)
        accounts.append({"email": email, "password": password, "role": role})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"purpose": "Local customer demo only; do not publish or commit", "accounts": accounts}, indent=2) + "\n", encoding="utf-8")
    print("Prepared user/admin demo accounts. Read credentials locally in runtime/demo/access.json; never commit this file.")


if __name__ == "__main__":
    main()
