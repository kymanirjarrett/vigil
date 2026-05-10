from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os

router = APIRouter()

ALGORITHM              = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _secret_key() -> str:
    key = os.getenv("VIGIL_JWT_SECRET")
    if not key:
        raise RuntimeError("VIGIL_JWT_SECRET is not set in .env")
    return key


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, _secret_key(), algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency — validates Bearer token and returns the username."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exc
        return username
    except JWTError:
        raise credentials_exc


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Validate credentials and return a JWT access token."""
    expected_username = os.getenv("VIGIL_USERNAME")
    expected_hash     = os.getenv("VIGIL_PASSWORD_HASH")

    if not expected_username or not expected_hash:
        raise HTTPException(status_code=500, detail="Auth credentials not configured in .env")

    if form_data.username != expected_username or \
       not pwd_context.verify(form_data.password, expected_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(form_data.username),
        "token_type":   "bearer",
    }
