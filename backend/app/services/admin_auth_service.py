import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.admin import Admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
JWT_SECRET_KEY = os.getenv("VAANI_ADMIN_JWT_SECRET", "CHANGE-ME-BEFORE-PRODUCTION")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("VAANI_ADMIN_TOKEN_MINUTES", "60"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def authenticate_admin(db: Session, email: str, password: str) -> Optional[Admin]:
    admin = db.query(Admin).filter(Admin.email == email.strip().lower()).first()
    if not admin or not admin.is_active:
        return None
    return admin if verify_password(password, admin.password_hash) else None


def create_access_token(admin: Admin) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin.id),
        "email": admin.email,
        "role": admin.role,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        admin_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise unauthorized
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin or not admin.is_active:
        raise unauthorized
    return admin
