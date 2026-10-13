import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

# Argon2id with the library's current recommended parameters (RFC 9106 low-memory profile).
_hasher = PasswordHasher()

# A real hash of a random password: verifying against it when an e-mail address is unknown
# keeps login timing the same for existing and non-existing accounts.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens (sessions, e-mail links) are stored only as a keyed hash, so a database leak doesn't expose them."""
    return hmac.new(get_settings().secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def anonymize_ip(ip: str | None) -> str | None:
    """Audit logs keep a keyed hash of the IP address, not the address itself."""
    if not ip:
        return None
    return hmac.new(get_settings().secret_key.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]
