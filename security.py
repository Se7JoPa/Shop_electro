"""Password hashing with per-password salt, using only Python's standard library."""
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        method, iterations, salt, expected = encoded.split('$')
        count = int(iterations)
        if method != 'pbkdf2_sha256' or not 100_000 <= count <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), count)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False
