from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from database import get_db
from models import User
import os

router = APIRouter()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _secret_key() -> str:
    key = os.getenv("VIGIL_JWT_SECRET")
    if not key:
        raise RuntimeError("VIGIL_JWT_SECRET is not set in .env")
    return key


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user.id), "email": user.email, "role": user.role, "exp": expire},
        _secret_key(),
        algorithm=ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise credentials_exc
    return user


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str


@router.post("/signup", status_code=201)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=req.email,
        password_hash=pwd_context.hash(req.password),
        role="analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": {"id": str(user.id), "email": user.email, "role": user.role},
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }
