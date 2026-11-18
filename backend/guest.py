"""The shared, read-only guest account behind "Try the demo".

Every visitor who clicks "Try the demo" gets their own tokens for this one
user. It has no usable password: password login always fails for it and
never counts toward lockout, so nobody can lock the shared account.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import User

GUEST_ROLE  = "guest"
# .invalid is reserved (RFC 2606), so this can never be a real mailbox.
GUEST_EMAIL = "guest@demo.invalid"
# Not a bcrypt hash, so verify_password() always returns False for it.
UNUSABLE_PASSWORD_HASH = "!"


class GuestAccountError(Exception):
    """The reserved guest email belongs to an account that is not the guest."""


def is_guest(user: User) -> bool:
    return user.role == GUEST_ROLE


def get_or_create_guest(db: Session) -> User:
    """Return the guest user, creating it if missing. Safe under concurrency:
    a duplicate insert hits the unique email index and is re-read."""
    user = db.query(User).filter(User.email == GUEST_EMAIL).first()
    if user is None:
        db.add(User(email=GUEST_EMAIL, password_hash=UNUSABLE_PASSWORD_HASH,
                    role=GUEST_ROLE, is_active=True))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        user = db.query(User).filter(User.email == GUEST_EMAIL).first()

    # Never hand out tokens for a non-guest account at this address.
    if user is None or user.role != GUEST_ROLE or not user.is_active:
        raise GuestAccountError("guest account is not available")
    return user
