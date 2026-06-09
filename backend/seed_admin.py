"""
Run once to create the initial admin user from env vars.
Usage: python seed_admin.py

Requires:
  VIGIL_ADMIN_EMAIL     - admin email address
  VIGIL_ADMIN_PASSWORD  - plaintext password (will be hashed)
  OR
  VIGIL_PASSWORD_HASH   - existing bcrypt hash (legacy, takes precedence)
"""
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from database import SessionLocal
from models import User

load_dotenv()

email = os.environ["VIGIL_ADMIN_EMAIL"].strip().lower()
existing_hash = os.getenv("VIGIL_PASSWORD_HASH")
plaintext = os.getenv("VIGIL_ADMIN_PASSWORD")

if not existing_hash and not plaintext:
    raise SystemExit("Set VIGIL_ADMIN_PASSWORD or VIGIL_PASSWORD_HASH in .env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = existing_hash if existing_hash else pwd_context.hash(plaintext)

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"Admin already exists: {email}")
    else:
        admin = User(
            email=email,
            password_hash=password_hash,
            role="admin",
        )
        db.add(admin)
        db.commit()
        print(f"Admin created: {email} (role=admin)")
finally:
    db.close()
