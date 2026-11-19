import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

_url = make_url(DATABASE_URL)
# SQLAlchemy 2.1 maps a bare postgresql:// URL to psycopg 3; this project ships psycopg2.
if _url.drivername == "postgresql":
    _url = _url.set(drivername="postgresql+psycopg2")

engine = create_engine(_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
