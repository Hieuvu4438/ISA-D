"""Explicit local account provisioning; passwords are read from the terminal only."""
import argparse
import re
from getpass import getpass

from app.application.account_service import AccountService
from app.data.account_repository import AccountRepository
from app.domain import AppError
from app.settings import Settings


def main():
    parser = argparse.ArgumentParser(description="Create a local user/admin; optional explicit demo-order ownership.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=("user", "admin"), default="user")
    parser.add_argument("--demo-customer", help="Explicit ownership mapping, e.g. C001; never accepted by the API")
    args = parser.parse_args()
    if args.demo_customer and not re.fullmatch(r"C[0-9]{3}", args.demo_customer):
        parser.error("--demo-customer must match C + three digits")
    password = getpass("Password (15–128 characters): ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match")
    settings = Settings.from_env()
    service = AccountService(AccountRepository(settings.root / "runtime/commerce/accounts.sqlite3"))
    try:
        account = service.register(args.email, args.name, password, "local-cli", args.role, args.demo_customer)
    except AppError as exc:
        parser.error(exc.message)
    print(f"Created {account['role']} account; credentials not printed.")


if __name__ == "__main__":
    main()
