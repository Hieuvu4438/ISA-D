import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from uuid import uuid4

from app.domain import AppError, normalize_text


def email_value(value):
    value = value.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
        raise AppError(422, "VALIDATION_ERROR", "Địa chỉ email không hợp lệ.", "email")
    return value


def name_value(value):
    value = normalize_text(value)
    if not 1 <= len(value) <= 80 or any(ord(c) < 32 for c in value):
        raise AppError(422, "VALIDATION_ERROR", "Tên hiển thị phải có 1–80 ký tự.", "display_name")
    return value


def hash_password(password, salt=None):
    # OWASP scrypt alternative: N=2^14, r=8, p=5 (16 MiB).
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), n=16384, r=8, p=5).hex()
    return f"scrypt$16384$8$5${salt}${digest}"


def password_value(value):
    if not 15 <= len(value) <= 128 or len(value.encode("utf-8")) > 512:
        raise AppError(422, "VALIDATION_ERROR", "Mật khẩu phải có 15–128 ký tự.", "password")
    return value


def verify_password(password, stored):
    salt = stored.split("$")[4]
    return hmac.compare_digest(hash_password(password, salt), stored)


class AccountService:
    def __init__(self, repository):
        self.repository = repository
        self.dummy_hash = hash_password(secrets.token_urlsafe(24))

    @staticmethod
    def public(account):
        return {key: account[key] for key in ("user_id", "email", "display_name", "role")}

    def throttle(self, email, peer, action="login"):
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        if not self.repository.throttle([(f"{action}:email:{email_hash}", 10), (f"{action}:peer:{peer}", 60)], int(time.time())):
            raise AppError(429, "AUTH_RATE_LIMITED", "Quá nhiều yêu cầu. Vui lòng thử lại sau 15 phút.", retryable=True)

    def register(self, email, name, password, peer, role="user", customer_id=None):
        email, name, password = email_value(email), name_value(name), password_value(password)
        self.throttle(email, peer, "register")
        try:
            return self.repository.create(str(uuid4()), email, name, hash_password(password), role, customer_id)
        except sqlite3.IntegrityError as exc:
            raise AppError(409, "ACCOUNT_EXISTS", "Không thể tạo tài khoản với thông tin này. Hãy đăng nhập hoặc dùng email khác.") from exc

    def login(self, email, password, peer):
        email = email_value(email)
        self.throttle(email, peer)
        account = self.repository.by_email(email)
        valid = verify_password(password, account["password_hash"] if account else self.dummy_hash)
        if not account or not valid or account["access_state"] != "active":
            raise AppError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu chưa đúng.")
        return account

    def require(self, token, role=None):
        account = self.repository.session(token, int(time.time()))
        if not account:
            raise AppError(401, "AUTH_REQUIRED", "Vui lòng đăng nhập để tiếp tục.")
        if role and account["role"] != role:
            raise AppError(403, "FORBIDDEN", "Tài khoản không có quyền thực hiện chức năng này.")
        return account

    def issue(self, account, old_token=None):
        token = secrets.token_urlsafe(32)
        self.repository.issue(account["user_id"], token, int(time.time()) + 8 * 3600, old_token, expected_epoch=account["auth_epoch"])
        return token

    def change_password(self, account, current, new, peer):
        password_value(new)
        self.throttle(account["email"], peer, "password")
        if not verify_password(current, account["password_hash"]):
            raise AppError(401, "INVALID_CREDENTIALS", "Mật khẩu hiện tại chưa đúng.", "current_password")
        updated = self.repository.change_password(account["user_id"], account["password_hash"], hash_password(new), expected_epoch=account["auth_epoch"])
        if not updated:
            raise AppError(409, "ACCOUNT_CHANGED", "Thông tin đã thay đổi. Hãy đăng nhập lại.")
        return updated
