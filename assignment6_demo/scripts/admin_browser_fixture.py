"""Explicit local E2E-only administrator fixture; never used by startup or CI defaults."""
import argparse
import os
from pathlib import Path

from app.application.account_service import AccountService
from app.data.account_repository import AccountRepository
from app.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "retire"))
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    if not args.email.startswith("admin-e2e-") or not args.email.endswith("@example.test"):
        parser.error("Only admin-e2e-* reserved example.test accounts are allowed")
    settings = Settings.from_env()
    if settings.root.resolve() != Path(__file__).resolve().parents[1]:
        parser.error("E2E fixture must stay in this workspace")
    repository = AccountRepository(settings.root / "runtime/commerce/accounts.sqlite3")
    if args.action == "provision":
        password = os.environ.get("CORTIS_E2E_ADMIN_PASSWORD", "")
        if len(password) < 24:
            parser.error("Set a random ephemeral CORTIS_E2E_ADMIN_PASSWORD, at least24 characters")
        AccountService(repository).register(args.email, "E2E operator", password, "e2e-cli", role="admin")
        print("Provisioned reserved E2E account; credentials omitted")
    else:
        with repository.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT user_id FROM accounts WHERE email=?", (args.email,)).fetchone()
            if row:
                db.execute("UPDATE accounts SET role='user' WHERE user_id=?", (row[0],))
                repository.invalidate_sessions(db, row[0])
        print("Retired reserved E2E administrator privileges and sessions")


if __name__ == "__main__":
    main()
