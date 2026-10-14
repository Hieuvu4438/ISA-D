"""Persistent identities and opaque sessions; no credentials enter API DTOs."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import time


class AccountRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','admin')),
                    customer_id TEXT UNIQUE, created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES accounts(user_id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    bucket TEXT NOT NULL, attempted_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_bucket ON auth_attempts(bucket, attempted_at);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, user_id, email, name, password_hash, role, customer_id=None):
        with self.connection() as db:
            db.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (user_id, email, name, password_hash, role, customer_id, int(time.time())))
        return self.by_email(email)

    def by_email(self, email):
        with self.connection() as db:
            row = db.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token, now):
        if not token or len(token) > 128:
            return None
        with self.connection() as db:
            row = db.execute("""SELECT a.* FROM accounts a JOIN sessions s ON a.user_id=s.user_id
                                WHERE s.token_hash=? AND s.expires_at>?""", (self.digest(token), now)).fetchone()
            return dict(row) if row else None

    def issue(self, user_id, token, expires_at, old_token=None):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
            if old_token:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (self.digest(old_token),))
            db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (self.digest(token), user_id, expires_at))

    def revoke(self, token):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (self.digest(token),))

    def throttle(self, buckets, now):
        """Atomic reservation: rejected requests never run an expensive password hash."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM auth_attempts WHERE attempted_at<=?", (now - 900,))
            for bucket, limit in buckets:
                count = db.execute("SELECT COUNT(*) FROM auth_attempts WHERE bucket=?", (bucket,)).fetchone()[0]
                if count >= limit:
                    return False
            db.executemany("INSERT INTO auth_attempts VALUES (?, ?)", [(bucket, now) for bucket, _ in buckets])
        return True

    def update_name(self, user_id, name):
        with self.connection() as db:
            db.execute("UPDATE accounts SET display_name=? WHERE user_id=?", (name, user_id))

    def change_password(self, user_id, expected_hash, new_hash):
        with self.connection() as db:
            changed = db.execute("UPDATE accounts SET password_hash=? WHERE user_id=? AND password_hash=?",
                                 (new_hash, user_id, expected_hash)).rowcount
            if changed:
                db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            return bool(changed)

    def counts(self):
        with self.connection() as db:
            return dict(db.execute("SELECT role, COUNT(*) FROM accounts GROUP BY role").fetchall())
