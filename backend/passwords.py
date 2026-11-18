"""Password hashing with bcrypt.

Calls the `bcrypt` library directly instead of going through passlib, which is
unmaintained and crashes on bcrypt >= 5.0 (its startup self-test hashes a
password longer than 72 bytes, which bcrypt 5 rejects). Existing `$2b$`
hashes created through passlib verify unchanged.
"""
import bcrypt

# bcrypt only reads the first 72 bytes of a password; longer ones are rejected
# at signup rather than silently truncated.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed stored hash, or a password over 72 bytes: never a match.
        return False
